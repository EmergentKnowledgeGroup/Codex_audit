---
name: monitor-codex-token-routing
description: Continuously monitor a live Codex orchestration tree and refresh compact agent telemetry plus human Markdown and HTML dashboards. Use for long-running multi-agent tasks, live token burn, route calibration, rework comparisons, stuck-agent detection, or when a Sol orchestrator needs inexpensive routing signals at decision boundaries.
---

# Monitor Codex token routing

Run the monitor once at the start of a long multi-agent phase. It reads local
Codex telemetry without modifying sessions, agents, code, hooks, or routing.

```powershell
python scripts/monitor_codex_routing.py --current --output-dir runtime/codex-routing
```

Use a task UUID instead of `--current` when `CODEX_THREAD_ID` is unavailable.
Add `--ledger calibration-ledger.json` for explicit acceptance/rework evidence.
Use `--once` for CI, testing, or a manual refresh.

The monitor atomically refreshes:

- `current-agent.json`: compact signals for the orchestrator.
- `current-report.md`: detailed user-readable scorecard.
- `dashboard.html`: self-refreshing local charts and tables.
- `calibration.json`: complete redacted evidence snapshot.
- `monitor-status.json`: freshness, generation count, and last error.

## Orchestrator contract

Read only `current-agent.json`, and only at a routing decision boundary:

- before new fan-out;
- after a worker or manager stops;
- before retrying or escalating effort;
- after compaction;
- at a phase boundary.

Do not repeatedly ingest the Markdown, HTML, or full calibration JSON. Treat all
signals as advisory. Quality-based route changes require explicit ledger data;
never infer acceptance from task completion.

## User report

Tell the user where `dashboard.html` and `current-report.md` live. Show or
summarize them on request. The dashboard refreshes itself in a browser but does
not expose a network server.

## Lifecycle and safety

- Stop with Ctrl-C. The final status becomes `stopped`.
- Keep the interval at 15 seconds or more for normal use.
- Do not install hooks or edit global/project configuration automatically.
- Do not cancel agents or change model/effort automatically.
- Keep identifiers redacted unless the user explicitly requests a private
  identifiable report.
- If a refresh fails, preserve the last good artifacts and record the error in
  `monitor-status.json`.
- Treat `open_child_links` as durable graph state, not proof that a child is
  currently executing. Verify live agent state before changing fan-out.

Codex lifecycle hooks may be offered as an optional user-approved optimization,
but the portable polling mode remains the default.
