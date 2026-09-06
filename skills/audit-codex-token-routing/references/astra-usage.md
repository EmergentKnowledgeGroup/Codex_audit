# Astra usage and attribution

Verified 2026-09-05 against the English official pages:
- https://learn.chatgpt.com/docs/pricing
- https://learn.chatgpt.com/docs/agent-configuration/speed

Standard credits per million uncached input / cached input / output:

| Model | Uncached | Cached | Output |
|---|---:|---:|---:|
| Astra | 250 | 25 | 1250 |
| Sol | 100 | 10 | 500 |
| Terra | 50 | 5 | 300 |
| Luna | 5 | 0.5 | 30 |

Astra costs 2.5x Sol for the same token mix at these standard rates. Fast mode
is a separate 2.5x Astra multiplier when applicable. Reasoning effort is not
a per-token discount. Rates can change; compare historical windows using one
clearly labeled current rate card unless actual historical rates are known.
Translated pricing pages may lag or disagree with the current English page;
do not silently combine their plan multipliers.

Calculate `(input-cached)*uncached_rate + cached*cached_rate + output*output_rate`,
then divide by one million. Input already includes cached tokens; output already
includes reasoning. A billion cached tokens and a billion uncached tokens have
very different costs. Pro is not documented here as a fixed raw-token allotment.

The local report measures available Codex usage, not every shared-account
feature, host, image charge, or cloud task. It cannot reverse engineer the
subscription denominator from a single percentage observation.

Use per-response records and event-time model settings. Never apply the current
SQLite model to an entire long-lived task that changed models. Keep unknown
models unpriced, distinguish response records from legacy fallback, and expose
missing/invalid records. Closed/idle children do not continuously consume tokens;
new model calls do. Sleep duration itself is not token usage, but repeatedly
waking a large-context controller can be costly.

Recommend a concrete next experiment from the user's work: move a repeated,
well-specified observation/check to deterministic automation or an already
qualified lower route; compare accepted outcomes, rework, elapsed time and
root-plus-child credits. A same-token repricing scenario isolates price only.
