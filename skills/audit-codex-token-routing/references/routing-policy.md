# Adaptive routing policy

Use this as a question set, not an enforcement table.

## Start with task evidence

Assess:

- Clarity: are the deliverable and acceptance criteria crisp?
- Blast radius: isolated file, subsystem, repo-wide, or release-wide?
- Judgment: mechanical work, ordinary tradeoffs, or architecture/security?
- Validation: deterministic tests, partial checks, or subjective review?
- Partition quality: can workers finish independently without shared writes?
- Context cost: how much history/tool output must each participant retain?

## Provisional starting routes

| Work shape | Starting route | Escalate only when |
|---|---|---|
| Mechanical lookup, extraction, inventory | Luna low | edge cases or interpretation fail |
| Ordinary implementation or tracing | Luna high | depth or tradeoffs require Terra medium |
| Scope interpretation, reconciliation, meaningful integration QA | Terra high | evidence conflicts or blast radius is material |
| Judgment-oriented QA/review | Sol low | architecture, security, release, or conflicting evidence appears |
| Architecture, security, release, conflicting-evidence judgment | Sol high | one bounded xhigh pass shows measured gain |

Use the lowest effort that passes the task's acceptance bar. Ordinary ambiguity
is a Terra problem, not an automatic Sol escalation. For clear, spec-gated work,
Luna-xhigh is the permitted control-plane route; do not use it as a reason to
make every worker xhigh. For worker work, escalate one axis at a time: effort,
then model, then delegation.

## Delegation gate

Delegate only when the lane is bounded, independently testable, and expected to
save wall-clock time or isolate noisy work. Prefer one child, start with at most
two, and default to `fork_turns=none`.

Every child needs one deliverable, owned scope, validation, compact return
format, and terminal condition. Close it after the accepted handoff. Do not use
repeated status polling or persistent workers by default.

## Context-pressure bands

Treat these as local test thresholds, not product limits:

- Below 50%: normal.
- 50-65%: checkpoint at the next phase boundary; avoid large raw output.
- 65-75%: artifact summaries only; avoid a new broad fan-out phase.
- Above 75%: finish the bounded phase, checkpoint, and compact before more broad
  work.

Compare these thresholds with the user's own success and usage data.

## Calibration loop

At a meaningful phase boundary—not after every tool call:

1. Capture a redacted calibration snapshot.
2. Record acceptance, rework, and defects in the explicit ledger.
3. Group only equivalent task families and matched pairs.
4. Compare estimated credits per accepted task, duration, rework, and defects.
5. Change one routing axis and rerun the same rubric.
6. Keep recommendations exploratory until repeated matched trials support them.

Automatic additional-turn counts are rework proxies only. The ledger is the
authority for actual acceptance and rework.

## Recommendation format

Return:

1. Measured usage drivers.
2. Task/codebase constraints.
3. Recommended route and why.
4. What not to change yet.
5. Paired benchmark design.
6. Stop/escalation conditions.
7. Confidence and missing evidence.
