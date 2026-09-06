---
name: audit-codex-token-routing
description: Audit Codex usage by chat, model, effort, and time window; generate offline visual reports and recommendations for Astra, Sol, Terra, Luna, context amplification, and subagents. Use for last-24-hour or since-reset audits, unexpected five-hour or weekly usage, routing comparisons, and token dashboards. Keep sources read-only and routing changes advisory unless separately authorized.
---

# Audit Codex Token Routing

Run the bundled analyzer before recommending changes:

```powershell
python scripts/audit_usage_window.py --hours 24 --output-dir <local-report-directory>
# Use an explicit offset and frozen cutoff for reproducible since-reset analysis:
python scripts/audit_usage_window.py --start <reset-ISO-timestamp> --end <cutoff-ISO-timestamp> --output-dir <local-report-directory>
python scripts/analyze_codex_tokens.py --current
python scripts/analyze_codex_tokens.py <task-id> [<task-id> ...] --out audit.json
python scripts/calibrate_codex_routing.py --current --markdown-out calibration.md --json-out calibration.json
```

Use `audit_usage_window.py` first for spending, time windows, model switches, or
Astra. It writes `usage.json`, `report.md`, and a self-contained printable
`dashboard.html`; show the HTML to the user and read compact JSON summaries for
agent decisions. It compares a preceding equal-duration baseline, uses
per-response usage where available, deduplicates response IDs, and falls back
to legacy token notifications only for turns without response records. Never
sum both record types. Older lifetime analyzers remain diagnostic tools; their
latest-state model and cumulative totals are not authoritative billing data.

When the user asks which chats consumed usage, explain that the local report
will contain chat names/IDs and use `--include-identifiers`. Keep that report
out of commits and public uploads. Default shareable output to redacted.

Record exact window boundaries and coverage. A rolling 24-hour window and a
since-reset window can differ; show both when reset evidence exists. Historical
rate-limit snapshots describe the whole account, not individual task billing.
Use the live usage tool when available to label the actual window duration;
do not assume `primary` always means five hours. Never redeem a reset for an audit.

Verify current official pricing before a cost interpretation; the bundled
rate card is dated 2026-09-05. `--rate-card` accepts a replacement with
`credits_per_million` keyed by exact model. Current-rate repricing is an
estimate, not a historical invoice or a fixed conversion to Pro allowance.
Track effort separately from service tier: low/light effort does not imply
Fast mode or a lower per-token rate. Unknown service tier stays unknown.

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
6. For an active multi-agent workflow, run `calibrate_codex_routing.py` at a
   phase boundary. Generate an acceptance ledger when outcomes/rework are not
   already recorded; never infer quality from `task_complete`.
7. Keep the result advisory. Do not edit code, `AGENTS.md`, `config.toml`, agent
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
- Compare routes only within equivalent task families or explicit matched pairs.
  Observational averages are confounded because stronger models often receive
  harder work.
- Still produce useful hypotheses: observation -> plausible cause -> next
  comparable real task -> acceptance/rework evidence -> keep or revise route.
  Label price-only same-token scenarios as counterfactuals. Do not claim a
  cheaper model will need identical tokens, or demand expensive replay of a
  whole project before offering any recommendation.

## Astra investigations

Read `references/astra-usage.md`. Decompose cost into cached input, uncached
input, and output before attributing burn to reasoning. Rank root-only and
root-plus-descendant usage separately. Review top-cost task action patterns
for repeated polling, broad output reads, retries, compaction, and rework.
Use Astra as a candidate for bounded difficult decisions when the codebase and
acceptance evidence justify it; never upgrade all orchestration or workers
solely because Astra is newer. Apply the user's explicit routing policy.

## Center-out routing candidate

For a clear project with an explicit specification, execution checklist,
blockerboard, and measurable acceptance criteria, treat Luna-xhigh as the
control-plane candidate. Route mechanical lookup/extraction/inventory to
Luna-low, ordinary implementation/tracing to Luna-high, deeper tradeoffs to
Terra-medium/high, judgment-oriented QA to Sol-low, and material
architecture/security/release/conflicting-evidence judgment to Sol-high. Use
xhigh only for one bounded pass after lower effort proves insufficient, except
for the explicitly tested Luna-xhigh control-plane route; do not fan out xhigh
workers by default.
