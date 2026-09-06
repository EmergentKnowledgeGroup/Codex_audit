# Codex Audit

Find out why a Codex task consumed so much of your five-hour or weekly usage,
then get recommendations tailored to your work—not a universal routing chart.

Codex Audit is a read-only, recommendation-only skill and local analyzer. It
uses the usage records already stored by Codex Desktop/CLI to show where tokens
went: parent context, subagents, model/effort selection, polling, tool output,
compaction, and repeated cached input.

It **does not** change your model, edit `config.toml` or `AGENTS.md`, modify your
codebase, close agents, or enforce a routing policy. You review every proposal.

The repository contains three installable skills:

- **Audit** (`audit-codex-token-routing`) diagnoses usage and calibrates routes.
- **Orchestrate** (`efficient-codex-orchestrator`) delegates with explicit model, effort, scope, and QA contracts.
- **Monitor** (`monitor-codex-token-routing`) continuously refreshes compact agent signals and live human reports.

## Why this exists

### Astra usage reports

Ask Codex: “Use audit-codex-token-routing to audit my last 24 hours by chat,
model, and effort, with a visual report and recommendations.” The analyzer
produces offline HTML, Markdown, and JSON reports. Standard-rate credit
estimates are not your subscription bill or a conversion to allowance usage.
See [Astra audit update](ASTRA_AUDIT_UPDATE.md) for usage and limitations.

Long agentic tasks can consume far more usage than their final answer suggests.
The expensive part is often not prose; it is repeatedly sending large
conversation history, tool results, and agent coordination back through a
model. Subagents can improve focus and wall-clock speed, but every child has its
own context and tool work.

GPT-5.6 is documented as output-token-efficient. That is not a promise that
every long Codex workflow uses fewer total tokens than GPT-5.5. This tool helps
you measure your actual workload before changing models or instructions.

## Fastest installation: ask Codex

Open a Codex task and paste:

```text
Use $skill-installer to install the skill from
https://github.com/EmergentKnowledgeGroup/Codex_audit/tree/main/skills/audit-codex-token-routing
```

Start a new task after installation so the skill is discovered.

### Manual installation

Clone the repository, then copy the skill directory into your personal Codex
skills folder:

```powershell
git clone https://github.com/EmergentKnowledgeGroup/Codex_audit.git
Copy-Item -Recurse -Force `
  .\Codex_audit\skills\audit-codex-token-routing `
  "$env:USERPROFILE\.codex\skills\audit-codex-token-routing"
```

On macOS or Linux:

```bash
git clone https://github.com/EmergentKnowledgeGroup/Codex_audit.git
cp -R Codex_audit/skills/audit-codex-token-routing ~/.codex/skills/
```

## Run it from Codex

For the current task:

```text
Use $audit-codex-token-routing to audit this task's token and subagent usage.
Inspect my codebase and task shape where useful, but make recommendations only.
Do not change my configuration, instructions, agents, or repository.
```

For a past task, provide its task ID:

```text
Use $audit-codex-token-routing to audit task
019xxxxxxxxxxxxxxxxxxxxxxxxxxxxx. Explain the biggest usage drivers and give
codebase-specific routing experiments. Recommendations only.
```

The agent should run the analyzer, inspect the relevant codebase conventions and
validation surfaces, and distinguish measured facts from hypotheses. A sprawling
monorepo, an isolated bug fix, a security review, and a documentation pass should
not receive the same recommendation.

## Run the analyzer directly

No third-party Python packages are required.

```powershell
python skills/audit-codex-token-routing/scripts/analyze_codex_tokens.py --current
```

Audit one or more saved task IDs:

```powershell
python skills/audit-codex-token-routing/scripts/analyze_codex_tokens.py `
  019xxxxxxxxxxxxxxxxxxxxxxxxxxxxx `
  019yyyyyyyyyyyyyyyyyyyyyyyyyyyyy `
  --out audit-results.json
```

The default report redacts task titles, codebase paths, usernames, and full
session paths. Use `--include-identifiers` only for a private local report.

Generate a provisional route recommendation:

```powershell
python skills/audit-codex-token-routing/scripts/route_task.py `
  --clarity 2 --blast 1 --judgment 0 --validation 2 --repeatable
```

This prints a recommendation. It does not apply it.

## Calibrate a live orchestration workflow

Create a redacted snapshot and a fill-in acceptance ledger:

```powershell
python skills/audit-codex-token-routing/scripts/calibrate_codex_routing.py `
  --current `
  --json-out calibration.json `
  --markdown-out calibration.md `
  --init-ledger calibration-ledger.json
```

The Markdown scorecard shows every root, manager, worker, and descendant with:

- Explicit model and effort.
- Final and gross tokens.
- Estimated credits using the documented rate card.
- Session duration and context pressure.
- Compactions, tool calls, coordination cost, and retained output volume.
- Additional-turn signals that may indicate follow-up or rework.

Logs cannot determine whether an edit was correct. Fill the generated ledger
with the task family, matched `pair_id`, outcome, actual rework rounds, defects,
and optional quality score. Unassessed runs remain `not_assessed`; the script
never converts `task_complete` into a quality claim.

Rerun after more work:

```powershell
python skills/audit-codex-token-routing/scripts/calibrate_codex_routing.py `
  --current `
  --ledger calibration-ledger.json `
  --baseline calibration.json `
  --json-out calibration-next.json `
  --markdown-out calibration-next.md
```

The new snapshot includes per-agent deltas, route cohorts within the same task
family, matched comparisons, and recommendation text such as “the accepted
Luna-high route used approximately X% fewer estimated credits than Terra-medium.”
Those statements remain exploratory until repeated equivalent trials exist.

Use `--rate-card your-rates.json` to replace the embedded rate card when Codex
pricing changes. Calibration never changes routing or configuration itself.

You can also ask the root orchestrator:

```text
Use $audit-codex-token-routing to calibrate this task now. Generate a redacted
scorecard and acceptance ledger, explain which fields require my judgment, and
recommend only the next matched routing experiment. Do not change routing or
configuration automatically.
```

## Monitor a long-running task continuously

```text
Use $monitor-codex-token-routing to monitor this task in the background. Keep
the output redacted and advisory. Read only the compact agent snapshot at
routing decision boundaries, and show me the human report or dashboard when I
ask.
```

Or run it directly:

```powershell
python skills/monitor-codex-token-routing/scripts/monitor_codex_routing.py `
  --current `
  --output-dir runtime/codex-routing
```

It atomically refreshes `current-agent.json`, `current-report.md`,
`dashboard.html`, `calibration.json`, and `monitor-status.json`. The dashboard
self-refreshes locally; it starts no server and uploads no telemetry. Stop with
Ctrl-C. Use `--once` to test without leaving a watcher running.

## What the report measures

- Root input, cached input, output, and reasoning-output tokens.
- Latest and peak context pressure.
- Durable child count and child usage by model/effort.
- Spawn attempts, history-fork choices, compactions, and aborted turns.
- Token usage associated with tool and coordination actions.
- Tool-result volume and inter-agent metadata.
- Per-agent and full-descendant calibration scorecards with optional acceptance
  and rework evidence.

These are local diagnostic records, not an invoice. Codex internals and schemas
can change. Five-hour and weekly allowance behavior can also depend on model,
context, reasoning, tools, retrieval, caching, and plan rules.

## Adaptive recommendations, not one-size-fits-all rules

The skill must inspect the user's actual task and codebase before recommending:

- Luna, Terra, or Sol.
- Low, medium, high, or xhigh reasoning.
- Single-agent versus delegated work.
- Child count and lifecycle.
- Context/compaction strategy.
- A controlled A/B test and acceptance criteria.

It must explain uncertainty and offer the smallest reversible experiment first.
It must never silently edit global instructions or model configuration.

## Enable Luna for native v2

Some Codex builds expose Luna to the CLI but filter it from native multi-agent
v2. The orchestrator includes an advanced, opt-in custom-catalog procedure with
schema validation, restart requirements, and an end-to-end native lifecycle
probe. Read [Enable Luna for native multi-agent v2](skills/efficient-codex-orchestrator/references/enable-luna-v2.md).

The repository never applies this global configuration automatically. Catalog
formats can change between Codex releases; obtain explicit user authorization
and validate the custom catalog before restarting.

## Experimental hierarchical routing

A Sol-led alternative for planning-heavy, QA-heavy, or higher-blast-radius work
is:

```text
Sol-low control agent for routine planning, delegation, and decisions
  -> Luna-xhigh handles one direct focused code/adjustment package
  -> Terra-medium handles lower-level interpreted problems
  -> Terra-high/xhigh handles deeper tracing and reconciliation
  -> Sol-low performs small judgment-oriented QA
  -> Sol-high/xhigh authors initial specs/docs, advises lower agents, and owns hard,
     large, high-blast-radius, architecture, security, release, or broad-QA decisions
```

This can reduce **weighted credit usage** even when it increases raw tokens,
because current published rates price Terra at roughly half of Sol and Luna at
roughly two-fifths of Terra. It can also fail spectacularly if the controller
misreads scope, workers duplicate work,
inherit large histories, loop on QA, or remain alive across phases.

Read [the hierarchical-routing guide](skills/audit-codex-token-routing/references/hierarchical-routing.md)
before trying it. Treat it as an experiment, not a default.

The repository also includes the optional
[`efficient-codex-orchestrator`](skills/efficient-codex-orchestrator/SKILL.md)
skill. To make it apply automatically to broad project work without prompting it
every time, install that skill and merge the compact rule set in
[`examples/global-agents-subagent-section.md`](examples/global-agents-subagent-section.md)
into your global `AGENTS.md`. Review the example first; nothing in this repository
edits global configuration automatically.

## Privacy and safety

- Analysis stays local unless you choose to share the output.
- Default JSON output is redacted, but task IDs and usage totals remain.
- Never publish private audit JSON without reviewing it.
- Do not delete session JSONL or SQLite databases as part of an audit.
- Do not treat token totals as exact billing or guaranteed allowance accounting.
- Do not let the skill alter a user's codebase or configuration unless the user
  separately and explicitly requests that change.

## Repository structure

```text
skills/audit-codex-token-routing/
  SKILL.md
  agents/openai.yaml
  scripts/analyze_codex_tokens.py
  scripts/calibrate_codex_routing.py
  scripts/route_task.py
  references/routing-policy.md
  references/hierarchical-routing.md
skills/efficient-codex-orchestrator/
  SKILL.md
  references/enable-luna-v2.md
  references/manager-worker-contract.md
examples/agents/luna-controller.toml
skills/monitor-codex-token-routing/
  SKILL.md
  scripts/monitor_codex_routing.py
examples/
tests/
```

## Status

Early public release. The analyzer is intentionally conservative and supports
the current local Codex session/state formats. Please open an issue with a
redacted reproduction if a newer Codex version changes those formats.

See [PATCH_NOTES.md](PATCH_NOTES.md) for the current release and monitor/routing
behavior changes.

## License

MIT
