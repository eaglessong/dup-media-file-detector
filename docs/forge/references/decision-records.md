# Decision records and durable state

Use docs/templates/adr.md for consequential choices: scope, architecture, public contract,
safety/error behavior, dependencies, performance tradeoffs and test realism. Do not
produce ADRs for naming or applying an already accepted rule. Link feature decisions
from its design and evidence; shared long-lived choices live in docs/decisions/.

Every decision records context/evidence, alternatives/tradeoffs, selected option,
consequences, decision-maker USER or AGENT, and revisit/rollback conditions. USER requires
actual quoted user input; an inferred preference is AGENT. An agent choosing a safe
default is not permission to rewrite an owner decision. Record implementation-time
choices back into the design in the same PR.

Read existing decisions before writing. A consequential reversal gets a new superseding
record with the original retained, the conflict surfaced, and affected artifacts updated.
Do not silently edit the owner's past answer. If concurrent work chose the same filename
or number, reconcile against current main without overwriting the other decision.

For a multi-wave program, reuse this repo's shared decisions rather than copying a
private program registry convention. One design/PR per coherent wave; keep completed
items, outstanding questions, evidence/PR links and next-wave dependencies in its brief
and evidence. A subsequent wave reads those decisions before scoping itself. New
irreversible/destructive steps require user authority; unattended runs stop or choose
an explicitly reversible alternative inside existing authority.

PRs surface USER and AGENT choices clearly. Unattended runs include a separate list of
consequential decisions made without the user and the questions that would have been
asked. Never invent a model/version/author trailer or import a company commit policy;
follow this repository's actual commit rules. Delivery evidence records what happened,
not merely what the plan intended. A PR approval is not automatically merge authority.
