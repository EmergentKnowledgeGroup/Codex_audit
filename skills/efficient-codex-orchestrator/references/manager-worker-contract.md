# Manager-worker contract

## Control-plane and Terra manager prompt requirements

For a clear spec-gated project, the root control plane should run at
`gpt-5.6-luna` with `xhigh` effort. Its job is routing, scope tracking, and
evidence compression—not broad implementation or final architectural judgment.
Escalate one bounded package to a `gpt-5.6-terra` manager at `high` when scope
interpretation, reconciliation, or meaningful QA is required.

Include:

- One bounded goal and explicit out-of-scope list.
- Original acceptance/QA rubric.
- Worker cap and runtime-capacity limit.
- Separate Luna ownership.
- Explicit model and reasoning effort on every spawn. Luna worker spawns use
  `gpt-5.6-luna`; a separate Sol-low reviewer is not a Luna worker spawn.
- `fork_turns=none` for workers.
- One rework round maximum.
- Compact evidence-packet schema.
- Terminal condition after handoff.

## Worker effort selection

| Worker shape | Explicit effort |
|---|---|
| Mechanical lookup, extraction, inventory | `low` |
| Exact small edit, named files/symbols, deterministic test | `high` for implementation; use Luna-low only when it is truly mechanical lookup/extraction |
| Normal bounded coding or tracing with clear acceptance | `high` |
| Difficult bounded logic or edge cases where high failed a rubric | `xhigh` |
| Judgment-oriented QA/review | Sol-low |
| Cross-module ambiguity, architecture, security, or release judgment | escalate to Terra/Sol |

Higher effort can use more reasoning tokens. Select it because the acceptance
rubric requires it, not because the model's per-token rate is unchanged. Use
xhigh for one bounded pass only after lower effort proves insufficient.

Native spawn shape:

```text
agent_type: worker
model: gpt-5.6-luna
reasoning_effort: low | medium | high | xhigh
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
