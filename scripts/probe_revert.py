"""Bounded synthetic revert measurements; never touches personal media.

The 10k case augments one real forward-writer manifest with synthetic registered
archive entries. It measures the revert planner, not 10k completed forward moves.
The 16MiB case is an actual forward/reverse round trip.
"""
from contextlib import closing
import json
from pathlib import Path
import resource
import sqlite3
import sys
import tempfile
import time
from unittest.mock import patch

from dup_media.move_fs import metadata
from dup_media.recovery import CONTROL, digest
from dup_media.relocate import Relocation
from dup_media.revert import Revert
from dup_media.scan import DEFAULT_EXTENSIONS, signature
from scripts.probe_move import Sink


def rss():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // (1024 if sys.platform == 'darwin' else 1)


def main():
    with tempfile.TemporaryDirectory() as t:
        base = Path(t).resolve(); original = base / 'original'; original.mkdir()
        for name in ['a.jpg', 'b.jpg']:
            (original / name).write_bytes(b'seed')
        archive = base / 'archive'
        assert Relocation(original, archive, base / 'journal').run(DEFAULT_EXTENSIONS, Sink(), False) == 0
        manifest = next((archive / CONTROL / 'operations').glob('*/manifest.sqlite'))
        with closing(sqlite3.connect(manifest)) as db:
            for i in range(9999):
                path = archive / f'synthetic-{i:05}.jpg'
                path.write_bytes(i.to_bytes(8, 'big') * 2)
                with path.open('rb') as stream:
                    db.execute('INSERT INTO items VALUES (?,?,?,?,?,?)',
                               (path.name, json.dumps(metadata(stream.fileno())), 16,
                                digest(stream), json.dumps(signature(path.stat())),
                                '.dup-media-stage-' + f'{i:032x}'))
            db.execute('UPDATE operation SET value=? WHERE key=?', ('10000', 'count')); db.commit()
        observations = {}
        plan = Revert.plan
        def observe(operation, scan):
            plan(operation, scan)
            observations['index_bytes'] = Path(scan.temp.name, 'index.sqlite').stat().st_size
        start = time.monotonic()
        with patch.object(Revert, 'plan', observe):
            assert Revert(archive).run(Sink(), True) == 0
        print(json.dumps(dict(phase='synthetic_registered_dry_run', registered_files=10000,
                              logical_bytes=4+9999*16, seconds=round(time.monotonic()-start,3),
                              manifest_bytes=manifest.stat().st_size, peak_rss_kib=rss(), **observations)), flush=True)
    with tempfile.TemporaryDirectory() as t:
        base = Path(t).resolve(); original = base / 'original'; original.mkdir()
        for name in ['a.jpg', 'b.jpg']:
            with (original / name).open('wb') as stream:
                for _ in range(16): stream.write(b'x' * 1024**2)
        archive = base / 'archive'
        assert Relocation(original, archive, base / 'journal').run(DEFAULT_EXTENSIONS, Sink(), False) == 0
        start = time.monotonic()
        assert Revert(archive).run(Sink(), False) == 0
        assert (original / 'b.jpg').stat().st_size == 16*1024**2
        assert not (archive / 'b.jpg').exists()
        print(json.dumps(dict(phase='real_round_trip_revert', restored_bytes=16*1024**2,
                              seconds=round(time.monotonic()-start,3), peak_rss_kib=rss())), flush=True)


if __name__ == '__main__':
    main()
