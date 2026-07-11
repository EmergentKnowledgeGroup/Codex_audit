---
name: efficient-codex-orchestrator
description: Choose and operate the smallest effective Codex agent topology for complex repository work while preserving one stable parent task. Use automatically for broad multi-step implementation, audit, research, or QA work that may benefit from delegation, especially when the user wants a Sol orchestrator with Terra or Luna workers, lower five-hour usage, bounded child lifecycles, or context-efficient execution.
---

# Efficient Codex Orchestrator

Keep the root task as the durable control thread. Own intent, decisions, user
communication, final integration, and checkpoint truth there. Do not create a
new parent task merely because context was compacted.

## Choose the topology

Use the least complex topology that fits:

1. **Root only:** one causal chain, routine work, shared edits, or weak validation.
2. **Root plus direct children:** 2-3 independent read-heavy or disjoint work
   packages with crisp acceptance criteria.
3. **Root -> Terra manager -> Luna workers:** several homogeneous, independently
   testable packages where Terra can QA mechanically without Sol-level judgment.

Do not use hierarchy merely because cheaper models exist.

## Root responsibilities

- Establish scope, acceptance, ownership, and stop conditions.
- Preserve decisions and evidence paths in the repository checkpoint.
- Keep raw scans, logs, and repetitive testing below the root.
- Perform final judgment only after receiving a compact evidence packet.
- Close completed child workstreams and continue the same root task after
  checkpoint/compaction.

## Hierarchical package

When topology 3 is justified:

1. Spawn one Terra-high manager with `fork_turns=none` and one bounded package.
2. Tell Terra to spawn at most two Luna medium/high workers unless verified
   runtime capacity permits more.
3. Give workers separate ownership, exact validation, one return schema, and no
   permission to spawn descendants.
4. Let Terra perform evidence-based QA and at most one targeted rework round.
5. Require Terra to return: decision, evidence, validations, unresolved risks,
   artifact paths, and recommended root action.
6. Close workers after handoff and close Terra after accepting its packet.

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
