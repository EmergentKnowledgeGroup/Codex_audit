# Manager-worker contract

## Sol control-plane and Terra manager prompt requirements

When active planning, delegation, or decision-making is required, use
`gpt-5.6-sol` at `low` as the routine control plane. Sol owns intent, scope,
evidence compression, and acceptance. Use Sol-high/xhigh for the initial
implementation spec/docs, senior-developer advice, hard or large projects, and
high-blast-radius decisions.

Delegate a direct, single-focus code or adjustment package to `gpt-5.6-luna`
at `xhigh`. Escalate a lower-level ambiguous problem to `gpt-5.6-terra` at
`medium`; use Terra-high/xhigh for deeper tracing, reconciliation, or difficult
cross-module work. Terra supports the decision; Sol retains consequential final
judgment.

Include:

- One bounded goal and explicit out-of-scope list.
- Original acceptance/QA rubric.
- Worker cap and runtime-capacity limit.
- Proof that the active native runtime permits the requested nesting depth; if
  not, keep all children directly under the root.
- Separate Luna ownership with one focused goal per worker.
- Explicit model and reasoning effort on every spawn. Luna worker spawns use
  `gpt-5.6-luna`; a separate Sol-low reviewer is not a Luna worker spawn.
- `fork_turns=none` for workers.
- One rework round maximum.
- Compact evidence-packet schema.
- Terminal condition after handoff.

## Worker effort selection

| Worker shape | Explicit effort |
|---|---|
| Mechanical lookup or extraction | Luna-low when delegation is actually worthwhile |
| Direct single-focus code or adjustment task | Luna-xhigh |
| Lower-level interpreted problem | Terra-medium |
| Deep tracing, reconciliation, difficult cross-module issue | Terra-high; Terra-xhigh for one bounded hard pass |
| Routine orchestration, planning, delegation, low-risk decision | Sol-low |
| Small judgment-oriented QA/review | Sol-low |
| Initial implementation spec/docs, broad QA, senior advice, architecture/security/release | Sol-high; Sol-xhigh for a bounded hard or high-impact pass |

Higher effort can use more reasoning tokens. Select it because the acceptance
rubric requires it. Luna-xhigh is intentional for direct focused execution;
Terra/Sol xhigh remains a bounded escalation. Initial implementation specs/docs
start at Sol-high and may start at Sol-xhigh for a hard or large project.

Native spawn shape:

```text
agent_type: worker
model: gpt-5.6-luna
reasoning_effort: xhigh
fork_turns: none
```

## Luna worker packet

```text
Goal: [one exact deliverable]
Ownership: [files, package, or evidence question]
Do not touch: [overlap and boundaries]
Validate: [one or two exact checks]
Return: result, evidence, validation, risks, artifact paths
Stop: after the return; do not broaden scope or spawn agents
```

## Terra return packet

```text
Decision: pass | partial | blocked
Completed packages: [...]
Evidence: [...]
Validations: [...]
Rework performed: none | one bounded round
Unresolved risks: [...]
Artifacts: [...]
Recommended root action: [...]
```

Keep the packet concise enough for the root to integrate without replaying
worker histories.
