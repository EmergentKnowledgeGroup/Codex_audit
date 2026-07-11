# Suggested global AGENTS.md subagent section

This makes the orchestrator skill automatic for broad work without making every
task a swarm.

```md
## Subagent usage
- For broad multi-step implementation, audit, research, or QA work, use the `efficient-codex-orchestrator` skill automatically to choose the smallest effective topology.
- The primary agent is the durable orchestrator. It owns planning, integration, user communication, final verification, and routine work.
- Delegate only independently bounded work when delegation materially saves elapsed time, isolates noisy context, or supplies genuinely independent review.
- Do not spawn for simple edits, file discovery, short reads, routine tests, or work the orchestrator can complete faster than briefing and integrating a child.
- When delegation is justified, prefer native in-app subagents. Use CLI subagents only when native agents fail or cannot attach cleanly.
- Start with at most two concurrent children. Use more only for demonstrably independent lanes with separate ownership. Keep default nesting depth at 1; raise it to 2 only for an explicit Terra-manager/Luna-worker package.
- Route mechanical lookup, extraction, and inventory to Luna medium/high; ordinary implementation, tracing, and QA to Terra medium/high; material architecture, security, release, or conflicting-evidence judgment to Sol high. Use xhigh only for one bounded pass after lower effort proves insufficient.
- Every spawn must set model and reasoning effort explicitly; never inherit an expensive parent route by accident.
- Default children to `fork_turns=none`. Provide exact paths, constraints, acceptance criteria, validation, compact return format, and terminal condition.
- Reuse a child for at most one tightly related follow-up. Otherwise accept its handoff and close it.
- Do not repeatedly poll agents. Continue useful independent work, then wait once when no other progress is possible.
- Children return decision-grade summaries and artifact paths, not raw logs. The orchestrator remains accountable for consequential work.
```
