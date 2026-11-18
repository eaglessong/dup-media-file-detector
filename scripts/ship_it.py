"""Atomic local ship-it bookkeeping. Does not execute or authorize remote actions."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import uuid

SHA = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
REPO = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*\Z")
STATUSES = {"in_progress", "waiting", "blocked", "merge_ready", "merged", "closed"}
TERMINAL = {"blocked", "merge_ready", "merged", "closed"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha(value: object) -> bool:
    return isinstance(value, str) and SHA.fullmatch(value) is not None


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate(state: object) -> dict:
    require(isinstance(state, dict), "state must be an object")
    require(type(state.get("schema_version")) is int and state["schema_version"] == 1,
            "unsupported state version")
    require(isinstance(state.get("repo"), str) and REPO.fullmatch(state["repo"]) is not None,
            "invalid repository")
    require(type(state.get("pr")) is int and state["pr"] > 0, "invalid PR number")
    require(type(state.get("max_rounds")) is int and state["max_rounds"] > 0,
            "max_rounds must be positive")
    require(type(state.get("round")) is int and 0 <= state["round"] <= state["max_rounds"],
            "invalid round count")
    require(type(state.get("no_merge")) is bool, "no_merge must be boolean")
    require(isinstance(state.get("status"), str) and state["status"] in STATUSES,
            "invalid status")
    require(sha(state.get("head")) and sha(state.get("base")), "invalid head/base SHA")
    for key in ("verified_head", "verified_base", "merge_commit"):
        require(key in state and (state[key] is None or sha(state[key])), f"invalid {key}")
    require(isinstance(state.get("history"), list), "history must be a list")
    failures = state.get("failures")
    require(isinstance(failures, dict) and all(nonempty(k) and type(v) is int and v > 0
                                              for k, v in failures.items()), "invalid failures")
    require("feedback_digest" in state and (state["feedback_digest"] is None or nonempty(state["feedback_digest"])),
            "invalid feedback digest")
    if state["status"] in {"merge_ready", "merged"}:
        require(state["verified_head"] == state["head"] and state["verified_base"] == state["base"],
                "final status requires recorded verification at current head/base")
    if state["status"] == "merged":
        require(not state["no_merge"] and sha(state.get("merge_commit")),
                "merged requires merge commit and no persisted --no-merge")
    return state


@contextmanager
def locked(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(str(path) + ".lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(descriptor)


def read(path: Path) -> dict:
    require(not path.is_symlink(), "state may not be a symlink")
    return validate(json.loads(path.read_text()))


def write(path: Path, state: dict) -> None:
    validate(state)
    require(not path.is_symlink(), "state may not be a symlink")
    descriptor, name = tempfile.mkstemp(prefix=".ship-it-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as stream:
            json.dump(state, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def initialize(path: Path, repo: str, pr: int, head: str, base: str,
               max_rounds: int = 20, no_merge: bool = False, new_run: bool = False) -> dict:
    candidate = {"schema_version": 1, "repo": repo, "pr": pr, "head": head, "base": base,
                 "max_rounds": max_rounds, "round": 0, "no_merge": no_merge,
                 "status": "in_progress", "verified_head": None, "verified_base": None,
                 "feedback_digest": None, "merge_commit": None, "failures": {}, "history": []}
    validate(candidate)
    with locked(path):
        if path.exists() or path.is_symlink():
            previous = read(path)
            require(previous["repo"] == repo and previous["pr"] == pr,
                    "state belongs to a different repo/PR")
            if new_run:
                archive = path.with_name(path.stem + ".archived-" + uuid.uuid4().hex + ".json")
                # Preserve the old file even if writing the new run fails.
                write(archive, previous)
                candidate["history"].append({"event": "new_run", "previous_state": archive.name})
            else:
                previous["no_merge"] = previous["no_merge"] or no_merge
                limit = min(previous["max_rounds"], max_rounds)
                require(limit >= previous["round"], "requested round cap is below completed rounds")
                previous["max_rounds"] = limit
                if previous["round"] == limit and previous["status"] in {"in_progress", "waiting"}:
                    previous["status"] = "blocked"
                    previous["history"].append({"event": "round_limit"})
                # Init is not observation: do not silently change refs or refresh receipts.
                candidate = previous
        write(path, candidate)
        return candidate


def apply(path: Path, action: str, payload: object = None, *, signature: str | None = None,
          status: str | None = None, merge_commit: str | None = None) -> dict:
    with locked(path):
        state = read(path)
        require(action in {"read", "round", "observe", "verify", "note", "failure", "finish"},
                "unknown state action")
        if action == "read":
            return state
        require(state["status"] not in TERMINAL, "terminal run: preserve it; new run needs fresh user scope")
        if action == "round":
            if state["round"] >= state["max_rounds"]:
                state["status"] = "blocked"
                state["history"].append({"event": "round_limit"})
            else:
                state["round"] += 1
                state["status"] = "in_progress"
        elif action == "observe":
            require(isinstance(payload, dict) and set(payload) == {"head", "base", "feedback_digest"},
                    "observation requires exactly head, base and feedback_digest")
            require(sha(payload["head"]) and sha(payload["base"]) and nonempty(payload["feedback_digest"]),
                    "invalid observation")
            if payload["head"] != state["head"] or payload["base"] != state["base"]:
                state["verified_head"] = state["verified_base"] = None
            state.update(payload)
            state["history"].append({"event": "observation", **payload})
        elif action == "verify":
            require(isinstance(payload, dict) and set(payload) == {"head", "base", "commands", "source"},
                    "verification requires exactly head, base, commands and source")
            require(payload["head"] == state["head"] and payload["base"] == state["base"],
                    "verification refs are stale")
            require(payload["source"] == "execution", "simulation belongs in note, not verification")
            commands = payload["commands"]
            require(isinstance(commands, list) and bool(commands) and all(
                isinstance(run, dict) and nonempty(run.get("command")) and
                type(run.get("exit_code")) is int and run["exit_code"] == 0 for run in commands),
                "verification needs nonempty commands with recorded exit_code 0")
            state["verified_head"], state["verified_base"] = state["head"], state["base"]
            state["history"].append({"event": "verification", **payload})
        elif action == "note":
            require(isinstance(payload, dict) and bool(payload), "note must be a nonempty object")
            state["history"].append({"event": "note", "details": payload})
        elif action == "failure":
            require(nonempty(signature), "failure requires a nonempty normalized signature")
            count = state["failures"].get(signature, 0) + 1
            state["failures"][signature] = count
            state["history"].append({"event": "failure", "signature": signature, "attempt": count})
            if count >= 3:
                state["status"] = "blocked"
        elif action == "finish":
            require(status in {"waiting", "blocked", "merge_ready", "merged", "closed"},
                    "invalid final status")
            state["status"] = status
            if status == "merged":
                require(sha(merge_commit), "merged needs --merge-commit")
                state["merge_commit"] = merge_commit
            state["history"].append({"event": "outcome", "status": status})
        write(path, state)
        return state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    for action in ("init", "read", "round", "observe", "verify", "note", "failure", "finish"):
        command = commands.add_parser(action)
        command.add_argument("--state", type=Path, required=True)
        if action == "init":
            command.add_argument("--repo", required=True)
            command.add_argument("--pr", type=int, required=True)
            command.add_argument("--head", required=True)
            command.add_argument("--base", required=True)
            command.add_argument("--max-rounds", type=int, default=20)
            command.add_argument("--no-merge", action="store_true")
            command.add_argument("--new-run", action="store_true")
        if action in {"observe", "verify", "note"}:
            command.add_argument("--input", type=Path, required=True)
        if action == "failure":
            command.add_argument("--signature", required=True)
        if action == "finish":
            command.add_argument("--status", required=True)
            command.add_argument("--merge-commit")
    args = parser.parse_args()
    try:
        if args.action == "init":
            state = initialize(args.state, args.repo, args.pr, args.head, args.base,
                               args.max_rounds, args.no_merge, args.new_run)
        else:
            payload = json.loads(args.input.read_text()) if hasattr(args, "input") else None
            state = apply(args.state, args.action, payload, signature=getattr(args, "signature", None),
                          status=getattr(args, "status", None), merge_commit=getattr(args, "merge_commit", None))
        print(json.dumps(state, indent=2))
        return 0
    except BlockingIOError:
        print("ERROR: state busy; do not remove another writer's lock", file=sys.stderr)
        return 3
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
