#!/usr/bin/env python3
"""Read-only, timestamp-bounded Codex usage audit with offline visual reports."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from analyze_codex_tokens import default_codex_home, safe_write, USAGE_FIELDS

RATE_CARD = {
    "verified_date": "2026-09-05",
    "source": "https://learn.chatgpt.com/docs/pricing",
    "basis": "Current standard credit rates applied to all selected usage; not historical billing",
    "credits_per_million": {
        "gpt-6-astra": {"input": 250, "cached_input": 25, "output": 1250},
        "gpt-5.6-sol": {"input": 100, "cached_input": 10, "output": 500},
        "gpt-5.6-terra": {"input": 50, "cached_input": 5, "output": 300},
        "gpt-5.6-luna": {"input": 5, "cached_input": .5, "output": 30},
        "gpt-5.5": {"input": 125, "cached_input": 12.5, "output": 750},
        "gpt-5.4": {"input": 62.5, "cached_input": 6.25, "output": 375},
        "gpt-5.4-mini": {"input": 18.75, "cached_input": 1.875, "output": 113},
        "gpt-daybreak-blue-latest": {"input": 100, "cached_input": 10, "output": 500},
    },
}


def stamp(value):
    result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timestamps must include an explicit UTC offset")
    return result.astimezone(timezone.utc)


def credits(usage, model, card=RATE_CARD):
    rate = card["credits_per_million"].get(model)
    if rate is None:
        return None
    return ((usage["input_tokens"] - usage["cached_input_tokens"]) * rate["input"]
            + usage["cached_input_tokens"] * rate["cached_input"]
            + usage["output_tokens"] * rate["output"]) / 1_000_000


def parse_session(path, task_id, start, end, coverage, action_start=None):
    """Prefer response records per turn; legacy notifications are a fallback only."""
    direct, legacy, limits, actions = [], [], [], Counter()
    action_start = action_start or start
    direct_turns = set()
    previous = None
    model = effort = tier = "unknown"
    turn = "unknown"
    created = None
    # Freeze bytes so a live writer cannot extend a scan indefinitely.
    remaining = path.stat().st_size
    with path.open("rb") as stream:
        while remaining > 0:
            raw = stream.readline(remaining)
            remaining -= len(raw)
            if not raw:
                break
            try:
                r = json.loads(raw)
                if not isinstance(r, dict):
                    raise ValueError()
                ts = stamp(r["timestamp"])
            except (ValueError, KeyError, UnicodeDecodeError):
                coverage["invalid_records"] += 1
                continue
            p = r.get("payload") or {}
            if not isinstance(p, dict):
                continue
            outer = r.get("type")
            kind = p.get("type", outer)
            if outer == "session_meta":
                try:
                    created = stamp(p.get("timestamp", r["timestamp"]))
                except ValueError:
                    pass
            if outer == "turn_context" or kind == "thread_settings_applied":
                s = p.get("thread_settings", p)
                settings = (s.get("collaboration_mode") or {}).get("settings") or {}
                model = settings.get("model") or s.get("model") or model
                effort = settings.get("reasoning_effort") or s.get("effort") or s.get("reasoning_effort") or effort
                tier = s.get("service_tier") or tier
                turn = p.get("turn_id", turn)
            if outer == "token_usage_record":
                if p.get("thread_id", task_id) != task_id:
                    coverage["foreign_usage_records_skipped"] += 1
                    continue
                usage = p.get("usage")
                response = p.get("response_id")
                event_turn = p.get("turn_id", turn)
            elif kind == "token_count":
                lim = p.get("rate_limits") or {}
                if start <= ts < end:
                    for key in ("primary", "secondary"):
                        win = lim.get(key)
                        if isinstance(win, dict):
                            limits.append({"timestamp": ts.isoformat(), "limit_id": lim.get("limit_id"),
                                           "window": key, **win})
                info = p.get("info") or {}
                cumulative = info.get("total_token_usage")
                signature = tuple((cumulative or {}).get(k, 0) for k in USAGE_FIELDS)
                if not cumulative or signature == previous:
                    if cumulative:
                        coverage["duplicate_cumulative_notifications"] += 1
                    continue
                previous = signature
                usage = info.get("last_token_usage")
                response = None
                event_turn = turn
            else:
                if action_start <= ts < end:
                    if kind in ("function_call", "custom_tool_call"):
                        actions[str(p.get("name", "unknown"))] += 1
                    elif outer == "compacted":
                        actions["context_compaction"] += 1
                continue
            if not usage or not start <= ts < end or (created and ts < created):
                continue
            u = {k: int(usage.get(k, 0)) for k in USAGE_FIELDS}
            if any(v < 0 for v in u.values()) or u["cached_input_tokens"] > u["input_tokens"]:
                coverage["invalid_usage_records"] += 1
                continue
            if outer == "token_usage_record":
                direct_turns.add(event_turn)
            event = {"timestamp": ts.isoformat(), "model": model, "effort": effort,
                     "service_tier": tier, "turn": event_turn, "response_id": response, **u}
            (direct if outer == "token_usage_record" else legacy).append(event)
    selected = direct + [x for x in legacy if x["turn"] not in direct_turns]
    coverage["response_records"] += len(direct)
    coverage["legacy_fallback_records"] += len(selected) - len(direct)
    coverage["mirrored_notifications_excluded"] += len(legacy) - (len(selected) - len(direct))
    return selected, limits, actions


def aggregate(events, card):
    result = {k: sum(x[k] for x in events) for k in USAGE_FIELDS}
    result["calls"] = len(events)
    priced = [credits(x, x["model"], card) for x in events]
    result["estimated_credits"] = round(sum(x for x in priced if x is not None), 6)
    result["unpriced_tokens"] = sum(e["total_tokens"] for e, c in zip(events, priced) if c is None)
    result["uncached_input_tokens"] = result["input_tokens"] - result["cached_input_tokens"]
    result["cache_hit_ratio"] = result["cached_input_tokens"] / result["input_tokens"] if result["input_tokens"] else 0
    result["mean_input_tokens"] = result["input_tokens"] / len(events) if events else 0
    return result


def collect(codex_home, state_db, start, end, include_identifiers=False, card=RATE_CARD):
    baseline_start = start - (end - start)
    coverage = Counter()
    with sqlite3.connect(state_db.resolve().as_uri() + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        columns = {r[1] for r in db.execute("PRAGMA table_info(threads)")}
        name_column = "name" if "name" in columns else "NULL AS name"
        rows = {r["id"]: dict(r) for r in db.execute(f"SELECT id,title,{name_column},rollout_path,updated_at FROM threads")}
        edges = {r["child_thread_id"]: r["parent_thread_id"] for r in db.execute("SELECT * FROM thread_spawn_edges")}
    candidates = {tid: Path(r["rollout_path"]) for tid, r in rows.items()
                  if r["updated_at"] >= baseline_start.timestamp()}
    # Include unindexed local/archived logs and resumed older tasks by modification time.
    for directory in ("sessions", "archived_sessions"):
        for p in (codex_home / directory).glob("**/*.jsonl"):
            if p.stat().st_mtime < baseline_start.timestamp():
                continue
            tid = p.stem[-36:]
            if tid not in candidates:
                candidates[tid] = p
    coverage["candidate_sessions"] = len(candidates)
    events, limits, actions_by_task, protected = [], [], {}, {state_db.resolve()}
    seen = set()
    for tid, path in candidates.items():
        protected.add(path.resolve())
        if not path.is_file():
            coverage["missing_sessions"] += 1
            continue
        usage, lim, acts = parse_session(path, tid, baseline_start, end, coverage, start)
        coverage["sessions_read"] += 1
        limits.extend(lim)
        actions_by_task[tid] = dict(acts)
        for e in usage:
            rid = e["response_id"]
            if rid and rid in seen:
                coverage["duplicate_response_ids"] += 1
                continue
            if rid:
                seen.add(rid)
            e["task_id"] = tid
            events.append(e)
    def ref(tid):
        if not tid:
            return None
        return tid if include_identifiers else "redacted:" + hashlib.sha256(tid.encode()).hexdigest()[:12]
    def root(tid):
        visited = set()
        while tid in edges and tid not in visited:
            visited.add(tid)
            tid = edges[tid]
        return tid
    current = [x for x in events if stamp(x["timestamp"]) >= start]
    before = [x for x in events if stamp(x["timestamp"]) < start]
    def grouped(key, source=current):
        groups = defaultdict(list)
        for e in source:
            groups[key(e)].append(e)
        return groups
    models = [{"model": k, **aggregate(v, card)} for k, v in grouped(lambda x: x["model"]).items()]
    routes = [{"route": k, **aggregate(v, card)} for k, v in grouped(lambda x: f'{x["model"]}/{x["effort"]}/{x["service_tier"]}').items()]
    chats = []
    for tid, es in grouped(lambda x: x["task_id"]).items():
        row = rows.get(tid, {})
        chats.append({"task_ref": ref(tid), "title": (row.get("name") or row.get("title") or tid) if include_identifiers else ref(tid),
                      "parent_ref": ref(edges.get(tid)), "root_ref": ref(root(tid)),
                      "models": sorted({x["model"] for x in es}), "efforts": sorted({x["effort"] for x in es}),
                      "actions": actions_by_task[tid], **aggregate(es, card)})
    roots = [{"root_ref": ref(k), **aggregate(v, card)} for k, v in grouped(lambda x: root(x["task_id"])).items()]
    hours = [{"hour": k, **aggregate(v, card)} for k, v in sorted(grouped(lambda x: x["timestamp"][:13] + ":00:00+00:00").items())]
    totals, baseline = aggregate(current, card), aggregate(before, card)
    for items in (models, chats, roots, routes):
        items.sort(key=lambda x: x["estimated_credits"], reverse=True)
    recommendations = []
    if models:
        lead = models[0]
        recommendations.append(f'{lead["model"]} accounts for {lead["estimated_credits"]:,.2f} estimated standard credits. Inspect its highest-cost tasks first; cost share does not establish task quality.')
    astra = [x for x in current if x["model"] == "gpt-6-astra"]
    if astra:
        a = aggregate(astra, card)
        sol = sum(credits(x, "gpt-5.6-sol", card) or 0 for x in astra)
        recommendations.append(f'Astra same-token-mix scenario: {a["estimated_credits"]:,.2f} credits versus {sol:,.2f} at Sol standard rates. This is a price-only counterfactual, not proof Sol can complete the work with the same calls or quality.')
        recommendations.append('Working hypothesis: keep routine monitoring, deterministic checks, and evidence gathering on a cheaper proven route; reserve Astra for a bounded decision where added capability changes acceptance. Test on the next comparable real task, recording acceptance and rework; no duplicate full-project replay required.')
    if totals["calls"]:
        recommendations.append(f'Mean request input is {totals["mean_input_tokens"]:,.0f} tokens across {totals["calls"]:,} calls. Reduce repeated context and avoid model-driven polling when a deterministic wait can do the job; low reasoning effort still processes input every call.')
    # Retain account-limit transitions, not thousands of unchanged notifications.
    transitions, previous_limits = [], {}
    for lim in sorted(limits, key=lambda x: x["timestamp"]):
        key = (lim.get("limit_id"), lim.get("window"), lim.get("window_minutes"))
        signature = (lim.get("used_percent"), lim.get("resets_at"))
        if previous_limits.get(key) != signature:
            transitions.append(lim)
            previous_limits[key] = signature
    limitations = [
        'Local available Codex logs only; cloud work, other hosts, deleted logs, and other shared-allowance features may be absent.',
        'Standard credits are a current-rate estimate, not a bill or a conversion into Pro weekly/five-hour percentage. No fixed billion-token plan allowance is assumed.',
        'Cached input is included in input; reasoning is included in output. Neither is added twice.',
        'Per-response records are deduplicated by response ID; legacy notifications are used only for turns without response records. Missing or malformed records are reported in coverage.',
        'Model/effort/service tier come from settings at event time, not the latest SQLite model. Unknown settings stay unknown. Standard estimates exclude Fast multipliers.',
        'Rate-limit snapshots are account-wide observations and may lag. They cannot be assigned to an individual chat as exact billed percentages.',
        'Baseline is the preceding equal-duration window repriced at the same current rates. Observational task mixes do not prove comparative model quality.',
    ]
    return {"schema_version": 1, "redacted": not include_identifiers, "recommendation_only": True,
            "window": {"start": start.isoformat(), "end": end.isoformat(), "baseline_start": baseline_start.isoformat()},
            "rate_card": card, "totals": totals, "baseline": baseline, "models": models,
            "routes": routes, "chats": chats, "roots": roots, "hours": hours,
            "coverage": dict(coverage), "rate_limit_observations": transitions,
            "recommendations": recommendations, "limitations": limitations}, protected


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--hours", type=float, default=24)
    p.add_argument("--start", help="Explicit reset/window start with UTC offset")
    p.add_argument("--end", help="Frozen cutoff with UTC offset; defaults to now")
    p.add_argument("--codex-home", type=Path, default=default_codex_home())
    p.add_argument("--state-db", type=Path)
    p.add_argument("--rate-card", type=Path)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--include-identifiers", action="store_true")
    p.add_argument("--force", action="store_true")
    args = p.parse_args()
    end = stamp(args.end) if args.end else datetime.now(timezone.utc)
    start = stamp(args.start) if args.start else end - timedelta(hours=args.hours)
    if start >= end:
        p.error("start must precede end")
    card = json.loads(args.rate_card.read_text(encoding="utf8")) if args.rate_card else RATE_CARD
    doc, protected = collect(args.codex_home, args.state_db or args.codex_home / "state_5.sqlite", start, end, args.include_identifiers, card)
    if args.rate_card:
        protected.add(args.rate_card.resolve())
    from render_usage_report import render_html, render_markdown
    outputs = {"usage.json": json.dumps(doc, indent=2, ensure_ascii=False),
               "report.md": render_markdown(doc), "dashboard.html": render_html(doc)}
    for name in outputs:
        target = (args.output_dir / name).resolve()
        if target in protected or (target.exists() and not args.force):
            p.error("Output protected or already exists; use a fresh output directory")
    for name, content in outputs.items():
        safe_write(args.output_dir / name, content, protected, args.force)
    print(json.dumps({"window": doc["window"], "totals": doc["totals"], "baseline": doc["baseline"], "models": doc["models"], "coverage": doc["coverage"], "output_dir": str(args.output_dir)}, indent=2))


if __name__ == "__main__":
    main()
