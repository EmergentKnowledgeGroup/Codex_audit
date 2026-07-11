# Manager-worker contract

## Terra manager prompt requirements

Include:

- One bounded goal and explicit out-of-scope list.
- Original acceptance/QA rubric.
- Worker cap and runtime-capacity limit.
- Separate Luna ownership.
- Explicit `model: gpt-5.6-luna` and `reasoning_effort` on every worker spawn.
- `fork_turns=none` for workers.
- One rework round maximum.
- Compact evidence-packet schema.
- Terminal condition after handoff.

## Worker effort selection

| Worker shape | Explicit effort |
|---|---|
| Exact small edit, named files/symbols, deterministic test | `medium` |
| Normal bounded coding with local decisions and self-review | `high` |
| Difficult bounded logic or edge cases where high failed a rubric | `xhigh` |
| Cross-module ambiguity, architecture, security, or release judgment | escalate to Terra/Sol |

Higher effort can use more reasoning tokens. Select it because the acceptance
rubric requires it, not because the model's per-token rate is unchanged.

Native spawn shape:

```text
agent_type: worker
model: gpt-5.6-luna
reasoning_effort: medium | high | xhigh
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
