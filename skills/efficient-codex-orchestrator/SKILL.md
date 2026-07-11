---
name: efficient-codex-orchestrator
description: Choose and operate a center-out Codex agent topology for spec-gated repository work while preserving one stable control task. Use automatically for broad implementation, audit, research, or QA work with clear contracts, checklists, blockerboards, or measurable acceptance criteria; route the control plane through Luna-xhigh, use Terra-high for judgment/integration, and escalate to Sol only for material architecture, security, release, or conflicting-evidence decisions.
---

# Efficient Codex Orchestrator

Keep the root task as the durable control thread. Own intent, decisions, user
communication, final integration, and checkpoint truth there. Do not create a
new parent task merely because context was compacted.

## Choose the topology

Use the least complex topology that fits:

1. **Root only:** one causal chain, routine work, shared edits, or weak validation.
2. **Luna-xhigh control plane -> direct workers:** a clear spec, execution
   checklist, blockerboard, measurable acceptance criteria, and independently
   testable packages.
3. **Luna-xhigh control plane -> Terra-high judgment manager -> Luna workers:**
   several packages where the controller must interpret scope, reconcile
   conflicting changes, or perform meaningful integration QA.
4. **Sol specialist escalation:** material architecture, security, release, or
   conflicting-evidence judgment. Do not make Sol the default controller merely
   because the repository is large.

Do not use hierarchy merely because cheaper models exist.

## Root responsibilities

- Establish scope, acceptance, ownership, and stop conditions. For a clear
  spec-gated project, the control plane is Luna-xhigh; if the active parent is
  already another model, do not restart solely to change the label.
- Preserve decisions and evidence paths in the repository checkpoint.
- Keep raw scans, logs, and repetitive testing below the root.
- Perform final judgment only after receiving a compact evidence packet.
- Close completed child workstreams and continue the same root task after
  checkpoint/compaction.

## Hierarchical package

When topology 3 is justified:

1. Spawn one Terra-high judgment manager with `fork_turns=none` and one bounded
   package. Use it when the Luna controller cannot safely interpret scope,
   reconcile changes, or perform the package's meaningful QA.
2. Tell Terra to spawn at most four Luna workers, with two as the default and
   more than two only when verified runtime capacity and separate ownership
   justify it. Require an explicit model and effort on every spawn: low for
   mechanical lookup/extraction/inventory, medium only for exact mechanical code
   edits with deterministic tests, high for normal bounded coding/tracing, and
   xhigh only for one difficult bounded task after lower effort proves
   insufficient.
3. Give workers separate ownership, exact validation, one return schema, and no
   permission to spawn descendants.
4. Let Terra perform integration and evidence-based QA, with at most one
   targeted rework round. Use Sol-low for a final judgment-oriented QA pass when
   the acceptance decision itself is consequential; deterministic tests do not
   need Sol.
5. Require Terra to return: decision, evidence, validations, unresolved risks,
   artifact paths, and recommended root action.
6. Close workers after handoff and close Terra after accepting its packet.

Do not let workers inherit the manager's model/effort implicitly.

## Default route matrix

Use the lowest route that can pass the explicit acceptance bar:

| Work shape | Default route | Escalate when |
|---|---|---|
| Mechanical lookup, extraction, inventory | Luna-low | edge cases or interpretation fail |
| Ordinary implementation or tracing | Luna-high | depth, cross-module reasoning, or tradeoffs require it; use Terra-medium |
| Scope interpretation, reconciliation, meaningful integration QA | Terra-high | evidence conflicts or blast radius is material |
| Judgment-oriented QA/review | Sol-low | the review exposes architecture, security, release, or conflicting-evidence judgment |
| Architecture, security, release, conflicting evidence | Sol-high | one bounded xhigh pass shows a measured gain |

Use xhigh only for one bounded pass after a lower effort proves insufficient.
The Luna-xhigh control plane is the explicit exception for a clear, spec-gated
project: do not fan out xhigh workers by default.

After a bounded package or a small batch of comparable packages, have the root
use the `audit-codex-token-routing` calibration script when installed. Running
`--current` inside a manager would calibrate only that manager subtree. Capture
the root scorecard once at the phase boundary; do not poll metrics after every call. Feed
accepted/rework/rejected outcomes into its ledger, then adjust one routing axis
only when matched evidence supports it.

For long-running work, start `monitor-codex-token-routing` once when installed.
Read its compact `current-agent.json` only before fan-out, after an agent stops,
before retry/escalation, after compaction, and at phase boundaries. Do not
ingest its full Markdown/HTML report into orchestrator context, and do not apply
monitor recommendations automatically.

Read `references/manager-worker-contract.md` before using hierarchy.

## Stop rules

- Stop fan-out when tasks overlap or depend sequentially on one another.
- Stop after a repeated blocker produces no new evidence.
- Stop the QA loop after one rework round; return the failure to the root.
- Do not repeatedly poll children. Continue useful root work, then wait once.
- Do not paste raw child logs into the root context.

## Context continuity

Use the visible context percentage and repository checkpoint. At rising pressure,
finish the current package, capture decisions/evidence/next command, close
children, and compact the same root task. Do not multiply user-visible parent
tasks solely to refresh context.
