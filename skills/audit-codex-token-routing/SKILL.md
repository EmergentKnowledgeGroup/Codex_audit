---
name: audit-codex-token-routing
description: Audit current or saved Codex tasks for token burn, cached-context amplification, model and effort choices, compactions, tool churn, and native subagent usage; then recommend codebase-specific routing and lifecycle experiments. Use when a user asks why five-hour or weekly Codex usage disappeared quickly, whether Sol/Terra/Luna or subagents are efficient, how to reduce task usage, or how to benchmark an orchestrator. Keep all actions read-only and recommendation-only unless the user separately authorizes changes.
---

# Audit Codex Token Routing

Run the bundled analyzer before recommending changes:

```powershell
python scripts/analyze_codex_tokens.py --current
python scripts/analyze_codex_tokens.py <task-id> [<task-id> ...] --out audit.json
```

Use `--codex-home` for a non-default Codex home. Use
`--include-identifiers` only when the user explicitly wants local paths, task
titles, and working directories in the report.

## Workflow

1. Measure root and durable-child token usage, current context pressure,
   compactions, action churn, and model/effort routes.
2. Inspect the user's actual task shape, repository instructions, architecture,
   validation strength, and whether work partitions are genuinely independent.
3. Separate facts from hypotheses. Local usage records do not reveal a complete
   billing or five-hour-limit formula.
4. Read `references/routing-policy.md` before proposing a route. Read
   `references/hierarchical-routing.md` only when multi-level delegation is
   relevant.
5. Recommend the smallest reversible change and a paired test with acceptance
   criteria. Never present thresholds as universal truths.
6. Keep the result advisory. Do not edit code, `AGENTS.md`, `config.toml`, agent
   files, or task state unless the user separately requests implementation.

## Guardrails

- Never delete or modify session JSONL, SQLite state, source repositories, or
  user configuration during an audit.
- Default to redacted output and warn before identifiers are included.
- Do not equate cached input with free input or add cached input to total input.
- Do not assume cheaper model means lower total usage; measure root plus children.
- Do not recommend more subagents merely to reduce Sol usage. Account for child
  work, coordination, QA, rework, and context duplication.
- Prefer repository evidence and controlled comparisons over a fixed routing
  infographic.
