# Manager-worker contract

## Terra manager prompt requirements

Include:

- One bounded goal and explicit out-of-scope list.
- Original acceptance/QA rubric.
- Worker cap and runtime-capacity limit.
- Separate Luna ownership.
- `fork_turns=none` for workers.
- One rework round maximum.
- Compact evidence-packet schema.
- Terminal condition after handoff.

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
