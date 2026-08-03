---
name: efficient-codex-orchestrator
description: Choose and operate the smallest effective Codex agent topology while preserving one stable control task. Use automatically for broad implementation, audit, research, or QA work with clear contracts or measurable acceptance criteria. Choose either Luna-centered execution for approved bounded work or a Sol-led senior mode for planning, delegation, specs, QA, hard problems, and higher-blast-radius decisions.
---

# Efficient Codex Orchestrator

Keep the root task as the durable control thread. Own intent, decisions, user
communication, final integration, and checkpoint truth there. Do not create a
new parent task merely because context was compacted.

## Choose the operating mode

### Mode A: Luna-centered execution

Use this only when scope and acceptance are already explicit. Luna-xhigh owns one
focused implementation or adjustment package at a time. It is not the default
planner, spec author, integration judge, or open-ended controller.

### Mode B: Sol-led senior orchestration

Use this when the root must plan, delegate, make decisions, author the initial
spec or documentation, supervise lower agents, or own a hard or large project.

- Use Sol-low for routine orchestration, planning against an approved spec,
  delegation, evidence compression, and low-blast-radius decisions.
- Use Sol-high for initial implementation specs/docs, consequential integration,
  broad QA, architecture/security/release judgment, or senior-developer advice.
- Use Sol-xhigh for a bounded initial spec/docs pass or hard decision whose
  complexity or blast radius justifies it. Do not keep the whole workflow at
  xhigh after the decision package is complete.
- Delegate direct, single-focus code or adjustment tasks to Luna-xhigh.
- Route lower-level problems needing some interpretation to Terra-medium; use
  Terra-high or Terra-xhigh for deeper tracing, reconciliation, and difficult
  cross-module issues.

Do not restart an already suitable root merely to change its model label. Apply
the routing policy to the next bounded child or phase.

## Choose the topology

Use the least complex topology that fits:

1. **Root only:** one causal chain, routine work, shared edits, or weak validation.
2. **Sol-low orchestrator -> Luna-xhigh focused workers:** approved scope with
   independently testable implementation packages.
3. **Sol-low orchestrator -> Terra manager/advisor -> Luna workers:** several
   packages needing tracing, reconciliation, or integration help. Start Terra at
   medium for lower-level problems; use high/xhigh for deeper issues.
4. **Sol-high/xhigh senior pass:** initial implementation spec/docs, hard or
   large projects, broad/high-blast-radius QA, material architecture, security,
   release, or conflicting-evidence judgment.

Do not use hierarchy merely because cheaper models exist.

## Root responsibilities

- Establish scope, acceptance, ownership, and stop conditions. Use Sol-low as
  the default orchestration and delegation layer when a parent must actively
  plan or decide. Use Luna-xhigh only for a direct bounded execution package.
- Preserve decisions and evidence paths in the repository checkpoint.
- Keep raw scans, logs, and repetitive testing below the root.
- Perform final judgment only after receiving a compact evidence packet.
- Close completed child workstreams and continue the same root task after
  checkpoint/compaction.

## Hierarchical package

When topology 3 is justified:

1. Spawn one Terra manager with `fork_turns=none` and one bounded package. Use
   Terra-medium for a lower-level problem that needs interpretation. Use
   Terra-high/xhigh for deep tracing, reconciliation, or difficult cross-module
   work. Keep final high-blast-radius judgment with Sol.
2. Tell Terra to spawn at most four Luna workers, with two as the default and
   more than two only when verified runtime capacity, nested spawning, and
   separate ownership justify it. Require an explicit model and effort on every
   spawn: low for worthwhile mechanical lookup/extraction/inventory and xhigh
   for one direct, single-focus code or adjustment package. Do not route an
   ambiguous or cross-module package to Luna merely by increasing effort.
3. Give workers separate ownership, exact validation, one return schema, and no
   permission to spawn descendants.
4. Let Terra perform integration support and evidence-based checks, with at most
   one targeted rework round. Use Sol-low for small judgment-oriented QA; use
   Sol-high for larger QA with meaningful blast radius. Deterministic tests do
   not need a separate Sol reviewer.
5. Require Terra to return: decision, evidence, validations, unresolved risks,
   artifact paths, and recommended root action.
6. Close workers after handoff and close Terra after accepting its packet.

Do not let workers inherit the manager's model/effort implicitly.

## Default route matrix

Use the lowest route that can pass the explicit acceptance bar:

| Work shape | Default route | Escalate when |
|---|---|---|
| Routine orchestration, planning, delegation, low-risk decisions | Sol-low | scope/spec creation or blast radius requires Sol-high |
| Initial implementation spec and foundational docs | Sol-high | use one bounded Sol-xhigh pass for large/hard work |
| Direct single-focus code or adjustment task | Luna-xhigh | ambiguity or cross-module depth requires Terra/Sol |
| Lower-level problem needing interpretation | Terra-medium | deeper tracing or reconciliation requires Terra-high |
| Deep issue, cross-module tracing, difficult reconciliation | Terra-high | use Terra-xhigh for one bounded hard pass |
| Small judgment-oriented QA/review | Sol-low | larger surface or blast radius requires Sol-high |
| Broad QA, architecture, security, release, conflicting evidence | Sol-high | one bounded Sol-xhigh pass when the decision warrants it |

Luna-xhigh is the explicit direct-execution route for one sharply focused code
package; do not fan out multiple xhigh workers by default. For Terra and Sol,
prefer the lowest effort that passes the acceptance bar and reserve xhigh for a
bounded deep pass. Initial implementation specs/docs are the exception: start
at Sol-high and use Sol-xhigh when the project is hard, large, or high impact.

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
monitor recommendations automatically. If `comparison_status` is
`descriptive_only` or `baseline_only`, use `working_hypothesis` and `next_test`
to choose the next bounded experiment; do not refuse to reason because quality
is unassessed. If it is `quality_gated`, the clean-route candidate may inform a
route change, but still preserve the user's acceptance bar and stop conditions.

Read `references/manager-worker-contract.md` before using hierarchy.
If native v2 does not expose Luna, read `references/enable-luna-v2.md`. Never
silently modify a user's global model catalog; apply that procedure only after
the user explicitly authorizes the configuration change.

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
