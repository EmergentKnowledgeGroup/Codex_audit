# Astra audit update — 2026-09-05

The audit skill now supports a frozen time window across local chats, with an
offline visual dashboard and a preceding equal-duration comparison. Personal
reports are local artifacts and are not part of this repository's public data.

Ask Codex:

> Use $audit-codex-token-routing to audit the last 24 hours. Show which chats
> and models used the most, create the visual report, and recommend the next
> practical improvement. If a reset occurred in that period, show a separate
> since-reset view. Keep the report local and do not change my routing automatically.

The reusable command is:

```powershell
python skills/audit-codex-token-routing/scripts/audit_usage_window.py --hours 24 --output-dir <local-report-folder>
```

Use `--start` and `--end` with explicit ISO time-zone offsets to audit a reset
interval or repeat a frozen comparison. Add `--include-identifiers` only for a
private report with task names and IDs. Output includes `usage.json`,
`report.md`, and a responsive, printable `dashboard.html` with model token and
credit shares, hourly activity, individual chats, and root-plus-child totals.

Changes:

- Added Astra standard-credit estimates and refreshed the calibration/monitor
  rate defaults to the official English pricing page verified September 5.
- Prefer newer per-response usage records; deduplicate response IDs and avoid
  counting their accompanying cumulative notifications again.
- Attribute model and effort at event time, including changes inside an old
  task; preserve unknown service tiers and unpriced models.
- Compare exact intervals instead of SQLite lifetime totals. Report missing
  or invalid source records and available account-limit transitions.
- Require useful, explicitly provisional recommendations even when quality
  outcomes have not yet been measured. Test the next comparable real task;
  a full duplicate project replay is not required.

Standard credits are not dollars, an invoice, or an exact percentage of a Pro
allowance. The dashboard applies one current rate card consistently to both
windows. Fast-mode costs and usage on other hosts or shared-account features
are outside that standard estimate. Older lifetime diagnostic/calibration
scripts still have approximate attribution; use the new window audit for
model changes and spending investigations.
