# Codex Audit patch notes

## 2026-08-02 — Luna v2 activation and Sol-led orchestration

- Added an opt-in, rollback-safe guide for exposing Luna to native multi-agent
  v2 through a validated custom model catalog.
- Added a Sol-led senior mode: Sol-low for routine orchestration and delegation;
  Sol-high/xhigh for initial specs/docs, senior advice, broad QA, and hard or
  high-blast-radius decisions.
- Routed direct focused code/adjustment packages to Luna-xhigh, lower-level
  interpreted problems to Terra-medium, and deeper issues to Terra-high/xhigh.
- Added native lifecycle and nested-spawn proof gates. CLI success alone is not
  treated as proof that Codex Desktop accepted Luna for native v2.

### Validation

- 31 unit tests passing.
- Efficient orchestrator skill validation and `git diff --check` passing.
- Independent Sol-low policy QA: GO after rollback and capability-proof fixes.

## 2026-07-11 — calibration, live monitoring, and center-out routing

This release adds the complete calibration and live-monitoring workflow for
long-running Codex orchestration:

- Added `audit-codex-token-routing` calibration scorecards with per-agent token,
  credit, duration, context, compaction, coordination, and rework signals.
- Added explicit acceptance/rework/defect ledgers and matched task-family
  comparisons. Quality claims remain gated on evidence rather than inferred from
  `task_complete`.
- Added `monitor-codex-token-routing`, which continuously refreshes a compact
  agent snapshot, Markdown report, redacted calibration JSON, local dashboard,
  and monitor status file.
- Added hypothesis-first monitoring. When quality evidence is incomplete, the
  monitor now reports a provisional route candidate, confidence, blockers, and a
  concrete matched next test instead of refusing to reason from the data.
- Added live `--baseline` support for phase-over-phase deltas.
- Added center-out routing guidance: Luna-xhigh control plane for clear
  spec-gated work; Luna-low for mechanical inventory/extraction; Luna-high for
  ordinary implementation/tracing; Terra-medium/high for depth, reconciliation,
  and meaningful integration QA; Sol-low for judgment QA; and Sol-high only for
  material architecture, security, release, or conflicting-evidence judgment.
- Added explicit controller/worker route handling, a default two-worker cap, and
  a hard four-worker maximum.
- Hardened read-only SQLite polling, malformed session handling, SQL identifier
  validation, output collision protection, and monitor failure preservation.

### Validation

- 31 unit tests passing.
- All three skills validate.
- Ruff and Python compilation pass.
- Live redacted monitor smoke emits a hypothesis and next test.
- Privacy scan is clean.

### Safety contract

The tools remain read-only and recommendation-only. A working hypothesis is
allowed and expected; automatic route/default promotion still requires explicit
quality evidence and user review.
