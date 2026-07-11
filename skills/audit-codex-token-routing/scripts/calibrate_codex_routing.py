#!/usr/bin/env python3
"""Build a read-only per-agent Codex routing calibration scorecard."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sqlite3
import statistics
from collections import defaultdict
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("codex_token_audit", HERE / "analyze_codex_tokens.py")
AUDIT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(AUDIT)

DEFAULT_RATE_CARD = {
    "effective_date": "2026-07-10",
    "source": "https://learn.chatgpt.com/docs/pricing#what-are-tokens-and-credits",
    "credits_per_million": {
        "gpt-5.6-sol": {"input": 125.0, "cached_input": 12.5, "output": 750.0},
        "gpt-5.6-terra": {"input": 62.5, "cached_input": 6.25, "output": 375.0},
        "gpt-5.6-luna": {"input": 25.0, "cached_input": 2.5, "output": 150.0},
        "gpt-5.5": {"input": 125.0, "cached_input": 12.5, "output": 750.0},
    },
}
VALID_OUTCOMES = {"accepted", "rejected", "partial", "blocked", "not_assessed"}
ALLOWED_TABLES = {"threads", "thread_spawn_edges"}
ALLOWED_TIMING_EXPRESSIONS = {
    "COALESCE(t.created_at_ms,t.created_at*1000)", "t.created_at*1000",
    "COALESCE(t.updated_at_ms,t.updated_at*1000)", "t.updated_at*1000",
    "t.agent_path", "NULL",
}


def ref(thread_id: str, include_identifiers: bool) -> str:
    return thread_id if include_identifiers else "redacted:" + hashlib.sha256(thread_id.encode()).hexdigest()[:12]


def db_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    if table not in ALLOWED_TABLES:
        raise AUDIT.AuditError(f"Unexpected state table: {table}")
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})")}


def discover_runs(root_id: str, state_db: Path) -> list[dict[str, Any]]:
    if not state_db.exists():
        raise AUDIT.AuditError(f"State database not found: {state_db}")
    with closing(AUDIT.readonly_connection(state_db)) as conn:
        conn.execute("PRAGMA query_only=ON")
        thread_cols = db_columns(conn, "threads")
        edge_cols = db_columns(conn, "thread_spawn_edges")
        required_threads = {"id", "rollout_path", "model", "reasoning_effort", "tokens_used"}
        required_edges = {"parent_thread_id", "child_thread_id", "status"}
        if not required_threads.issubset(thread_cols) or not required_edges.issubset(edge_cols):
            raise AUDIT.AuditError("State database schema lacks required thread/edge columns")
        created = "COALESCE(t.created_at_ms,t.created_at*1000)" if "created_at_ms" in thread_cols else "t.created_at*1000"
        updated = "COALESCE(t.updated_at_ms,t.updated_at*1000)" if "updated_at_ms" in thread_cols else "t.updated_at*1000"
        agent_path = "t.agent_path" if "agent_path" in thread_cols else "NULL"
        if {created, updated, agent_path} - ALLOWED_TIMING_EXPRESSIONS:
            raise AUDIT.AuditError("Unexpected state timing expression")
        query = f"""
        WITH RECURSIVE tree(thread_id,parent_thread_id,depth,edge_status) AS (
          SELECT ?,NULL,0,'root'
          UNION
          SELECT e.child_thread_id,e.parent_thread_id,tree.depth+1,e.status
          FROM thread_spawn_edges e JOIN tree ON e.parent_thread_id=tree.thread_id
        )
        SELECT tree.thread_id,tree.parent_thread_id,tree.depth,tree.edge_status,
               t.rollout_path,t.model,t.reasoning_effort,t.tokens_used,
               {created},{updated},{agent_path}
        FROM tree JOIN threads t ON t.id=tree.thread_id
        ORDER BY tree.depth,5
        """
        rows = conn.execute(query, (root_id,)).fetchall()
    return [{
        "thread_id": row[0], "parent_thread_id": row[1], "depth": int(row[2]),
        "edge_status": row[3], "rollout_path": row[4], "model": row[5] or "unknown",
        "reasoning_effort": row[6] or "unknown", "db_tokens": int(row[7] or 0),
        "created_at_ms": int(row[8] or 0), "updated_at_ms": int(row[9] or 0),
        "agent_path": row[10],
    } for row in rows]


def session_duration(path: Path) -> tuple[float | None, int]:
    first: datetime | None = None
    last: datetime | None = None
    invalid = 0
    try:
        with path.open("rb") as stream:
            for raw_line in stream:
                try:
                    line = raw_line.decode("utf-8")
                except UnicodeDecodeError:
                    invalid += 1
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    invalid += 1
                    continue
                if not isinstance(record, dict):
                    invalid += 1
                    continue
                raw = record.get("timestamp")
                if not raw:
                    continue
                try:
                    timestamp = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                except ValueError:
                    continue
                first = first or timestamp
                last = timestamp
    except (OSError, UnicodeDecodeError):
        return None, invalid
    return ((last - first).total_seconds() if first and last else None), invalid


def credit_estimate(usage: dict[str, Any], model: str, rate_card: dict[str, Any]) -> float | None:
    rate_key = "gpt-5.6-sol" if model == "gpt-5.6" else model
    rates = rate_card.get("credits_per_million", {}).get(rate_key)
    if not rates:
        return None
    input_tokens = int(usage.get("input_tokens", 0))
    cached = int(usage.get("cached_input_tokens", 0))
    output = int(usage.get("output_tokens", 0))
    uncached = max(0, input_tokens - cached)
    return round((uncached * rates["input"] + cached * rates["cached_input"] + output * rates["output"]) / 1_000_000, 6)


def load_ledger(path: Path | None) -> dict[str, dict[str, Any]]:
    if not path:
        return {}
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AUDIT.AuditError(f"Invalid calibration ledger: {exc}") from exc
    evaluations = document.get("evaluations", []) if isinstance(document, dict) else []
    result = {}
    for index, item in enumerate(evaluations):
        if not isinstance(item, dict) or not item.get("task_ref"):
            raise AUDIT.AuditError(f"Ledger evaluation {index} needs task_ref")
        outcome = item.get("outcome", "not_assessed")
        if outcome not in VALID_OUTCOMES:
            raise AUDIT.AuditError(f"Ledger evaluation {index} has invalid outcome: {outcome}")
        for field in ("rework_rounds", "defects"):
            value = item.get(field)
            if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
                raise AUDIT.AuditError(f"Ledger evaluation {index} field {field} must be a non-negative integer or null")
        quality = item.get("quality_score")
        if quality is not None and (isinstance(quality, bool) or not isinstance(quality, (int, float)) or not 0 <= quality <= 5):
            raise AUDIT.AuditError(f"Ledger evaluation {index} quality_score must be 0-5 or null")
        for field in ("task_family", "pair_id"):
            if item.get(field) is not None and not isinstance(item.get(field), str):
                raise AUDIT.AuditError(f"Ledger evaluation {index} field {field} must be a string")
        result[str(item["task_ref"])] = item
    return result


def make_runs(root_id: str, state_db: Path, include_identifiers: bool,
              ledger: dict[str, dict[str, Any]], rate_card: dict[str, Any]) -> tuple[list[dict[str, Any]], set[Path]]:
    rows = discover_runs(root_id, state_db)
    runs = []
    protected = {state_db.resolve()}
    for row in rows:
        path = Path(row["rollout_path"]).expanduser()
        protected.add(path.resolve())
        task_ref = ref(row["thread_id"], include_identifiers)
        parent_ref = ref(row["parent_thread_id"], include_identifiers) if row["parent_thread_id"] else None
        evaluation = ledger.get(task_ref, {})
        data_quality: list[str] = []
        if path.exists():
            report = AUDIT.analyze(path, row["thread_id"], state_db, include_identifiers, True)
            duration, invalid = session_duration(path)
        else:
            report = {"totals": {}, "gross_inference_usage": {}, "cached_input_ratio": 0,
                      "model_context_window": 0, "latest_context_pressure": None,
                      "compactions": 0, "model_inference_events": 0,
                      "event_counts": {}, "action_usage_approximate": [], "tool_output_bytes": {}}
            duration, invalid = None, 0
            data_quality.append("session_missing")
        if invalid:
            data_quality.append(f"invalid_jsonl_lines:{invalid}")
        gross = report.get("gross_inference_usage") or report.get("totals") or {}
        event_counts = report.get("event_counts", {})
        action_rows = {item.get("name"): item for item in report.get("action_usage_approximate", [])}
        coordination_names = {"spawn_agent", "wait_agent", "list_agents", "send_message", "followup_task", "interrupt_agent"}
        coordination_tokens = sum(int(action_rows.get(name, {}).get("total_tokens", 0)) for name in coordination_names)
        tool_calls = int(event_counts.get("function_call", 0)) + int(event_counts.get("custom_tool_call", 0))
        task_turns = int(event_counts.get("task_started", 0))
        run = {
            "task_ref": task_ref, "parent_ref": parent_ref, "depth": row["depth"],
            "route": f"{row['model']}/{row['reasoning_effort']}", "model": row["model"],
            "reasoning_effort": row["reasoning_effort"], "edge_status": row["edge_status"],
            "observed_duration_seconds": round(max(0, row["updated_at_ms"] - row["created_at_ms"]) / 1000, 3),
            "session_duration_seconds": round(duration, 3) if duration is not None else None,
            "final_tokens": report.get("totals", {}), "gross_tokens": gross,
            "gross_total_tokens": int(gross.get("total_tokens", row["db_tokens"])),
            "estimated_credits": credit_estimate(gross, row["model"], rate_card),
            "cached_input_ratio": report.get("cached_input_ratio"),
            "latest_context_pressure": report.get("latest_context_pressure"),
            "model_context_window": report.get("model_context_window"),
            "inference_events": report.get("model_inference_events", 0),
            "compactions": report.get("compactions", 0), "tool_calls": tool_calls,
            "coordination_tokens_approx": coordination_tokens,
            "tool_output_bytes": sum(int(value) for value in report.get("tool_output_bytes", {}).values()),
            "additional_task_turns_proxy": max(0, task_turns - 1),
            "task_family": evaluation.get("task_family"), "pair_id": evaluation.get("pair_id"),
            "outcome": evaluation.get("outcome", "not_assessed"),
            "rework_rounds": evaluation.get("rework_rounds"), "defects": evaluation.get("defects"),
            "quality_score": evaluation.get("quality_score"), "data_quality": data_quality,
        }
        if include_identifiers:
            run["agent_path"] = row["agent_path"]
            run["rollout_path"] = str(path)
        runs.append(run)
    return runs, protected


def apply_baseline(runs: list[dict[str, Any]], path: Path | None) -> None:
    if not path:
        return
    try:
        prior = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AUDIT.AuditError(f"Invalid baseline snapshot: {exc}") from exc
    previous = {item.get("task_ref"): item for item in prior.get("runs", [])}
    for run in runs:
        old = previous.get(run["task_ref"])
        if not old:
            continue
        run["delta_gross_tokens"] = run["gross_total_tokens"] - int(old.get("gross_total_tokens", 0))
        current_credits, old_credits = run.get("estimated_credits"), old.get("estimated_credits")
        if current_credits is not None and old_credits is not None:
            run["delta_estimated_credits"] = round(current_credits - float(old_credits), 6)


def median(values: list[float | int | None]) -> float | None:
    cleaned = [float(value) for value in values if value is not None]
    return round(statistics.median(cleaned), 6) if cleaned else None


def build_cohorts(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        if run.get("task_family"):
            groups[(run["task_family"], run["route"])].append(run)
    cohorts = []
    for (family, route), items in sorted(groups.items()):
        evaluated = [item for item in items if item["outcome"] != "not_assessed"]
        accepted = [item for item in evaluated if item["outcome"] == "accepted"]
        cohorts.append({
            "task_family": family, "route": route, "runs": len(items),
            "evaluated": len(evaluated), "accepted": len(accepted),
            "acceptance_rate": round(len(accepted) / len(evaluated), 4) if evaluated else None,
            "median_gross_tokens": median([item["gross_total_tokens"] for item in items]),
            "median_estimated_credits": median([item["estimated_credits"] for item in items]),
            "median_duration_seconds": median([item["session_duration_seconds"] for item in items]),
            "median_rework_rounds": median([item["rework_rounds"] for item in evaluated]),
            "median_defects": median([item["defects"] for item in evaluated]),
        })
    return cohorts


def build_pairs(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pairs: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        if run.get("task_family") and run.get("pair_id"):
            pairs[(run["task_family"], run["pair_id"])].append(run)
    comparisons = []
    for (family, pair_id), items in sorted(pairs.items()):
        assessed = [item for item in items if item["outcome"] != "not_assessed"]
        if len(assessed) < 2:
            continue
        accepted = [item for item in assessed if item["outcome"] == "accepted" and item["estimated_credits"] is not None]
        clean = [item for item in accepted if item.get("defects") == 0 and item.get("rework_rounds") == 0]
        winner = min(accepted, key=lambda item: item["estimated_credits"]) if accepted else None
        clean_winner = min(clean, key=lambda item: item["estimated_credits"]) if clean else None
        comparisons.append({
            "task_family": family, "pair_id": pair_id,
            "routes": [{"route": item["route"], "outcome": item["outcome"],
                        "estimated_credits": item["estimated_credits"],
                        "gross_tokens": item["gross_total_tokens"],
                        "rework_rounds": item["rework_rounds"], "defects": item["defects"]}
                       for item in assessed],
            "lowest_credit_accepted_route": winner["route"] if winner else None,
            "lowest_credit_clean_route": clean_winner["route"] if clean_winner else None,
            "exploratory_only": True,
        })
    return comparisons


def recommendations(comparisons: list[dict[str, Any]]) -> list[str]:
    notes = []
    for comparison in comparisons:
        accepted = [item for item in comparison["routes"] if item["outcome"] == "accepted" and item["estimated_credits"] is not None]
        clean = [item for item in accepted if item.get("defects") == 0 and item.get("rework_rounds") == 0]
        reworked_or_defective = [item for item in accepted if item not in clean]
        rejected = [item for item in comparison["routes"] if item["outcome"] in {"rejected", "partial"}]
        if clean:
            best = min(clean, key=lambda item: item["estimated_credits"])
            if rejected:
                notes.append(f"{comparison['task_family']} / {comparison['pair_id']}: test {best['route']} as the next candidate; it was accepted while {', '.join(item['route'] for item in rejected)} required rejection/partial handling.")
            if reworked_or_defective:
                notes.append(f"{comparison['task_family']} / {comparison['pair_id']}: {best['route']} was accepted with zero recorded rework/defects; {', '.join(item['route'] for item in reworked_or_defective)} had rework, defects, or missing quality qualifiers. Compare full package cost in repeated trials.")
            elif len(clean) > 1:
                worst = max(clean, key=lambda item: item["estimated_credits"])
                if worst["estimated_credits"] > 0:
                    saving = round((worst["estimated_credits"] - best["estimated_credits"]) / worst["estimated_credits"] * 100, 1)
                    notes.append(f"{comparison['task_family']} / {comparison['pair_id']}: {best['route']} was accepted with approximately {saving}% fewer estimated credits than {worst['route']}; repeat matched trials before changing defaults.")
    return notes or ["No assessed matched comparison supports a routing change yet. Fill the acceptance ledger and collect equivalent pairs."]


def ledger_template(runs: list[dict[str, Any]]) -> dict[str, Any]:
    return {"schema_version": 1, "evaluations": [{
        "task_ref": run["task_ref"], "observed_route": run["route"],
        "depth": run["depth"], "observed_gross_tokens": run["gross_total_tokens"],
        "task_family": "", "pair_id": "",
        "outcome": "not_assessed", "rework_rounds": None, "defects": None,
        "quality_score": None, "notes": "",
    } for run in runs if run["depth"] > 0]}


def markdown(document: dict[str, Any]) -> str:
    lines = ["# Codex routing calibration", "", "> Recommendation-only. Token/credit figures are local estimates, not billing guarantees.", "",
             "## Evidence quality", "",
             f"- Runs observed: {len(document['runs'])}",
             f"- Runs assessed in ledger: {sum(run['outcome'] != 'not_assessed' for run in document['runs'])}",
             f"- Matched comparisons: {len(document['paired_comparisons'])}",
             f"- Rate card effective date: {document['rate_card']['effective_date']}", "",
             "## Per-agent scorecard", "",
             "| Agent | Depth | Route | Gross tokens | Delta tokens | Est. credits | Delta credits | Duration | Coord. tokens | Compactions | Turns+ | Rework | Outcome |",
             "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for run in document["runs"]:
        lines.append(f"| {run['task_ref']} | {run['depth']} | {run['route']} | {run['gross_total_tokens']:,} | {run.get('delta_gross_tokens', 'NA')} | {run['estimated_credits'] if run['estimated_credits'] is not None else 'NA'} | {run.get('delta_estimated_credits', 'NA')} | {run['session_duration_seconds'] if run['session_duration_seconds'] is not None else 'NA'}s | {run['coordination_tokens_approx']:,} | {run['compactions']} | {run['additional_task_turns_proxy']} | {run['rework_rounds'] if run['rework_rounds'] is not None else 'NA'} | {run['outcome']} |")
    lines.extend(["", "`Turns+` is an automatic follow-up/rework proxy, not a quality verdict.", "", "## Route cohorts", "",
                  "| Task family | Route | n | Accepted/evaluated | Median tokens | Median credits | Median rework |",
                  "|---|---|---:|---:|---:|---:|---:|"])
    for cohort in document["cohorts"]:
        lines.append(f"| {cohort['task_family']} | {cohort['route']} | {cohort['runs']} | {cohort['accepted']}/{cohort['evaluated']} | {cohort['median_gross_tokens'] if cohort['median_gross_tokens'] is not None else 'NA'} | {cohort['median_estimated_credits'] if cohort['median_estimated_credits'] is not None else 'NA'} | {cohort['median_rework_rounds'] if cohort['median_rework_rounds'] is not None else 'NA'} |")
    lines.extend(["", "## Matched comparisons", "",
                  "| Task family | Pair | Routes assessed | Lowest-credit accepted (descriptive) | Lowest-credit clean (decision candidate) |",
                  "|---|---|---|---|---|"])
    for comparison in document["paired_comparisons"]:
        routes = ", ".join(f"{item['route']} ({item['outcome']}, {item['estimated_credits'] if item['estimated_credits'] is not None else 'NA'} credits)" for item in comparison["routes"])
        lines.append(f"| {comparison['task_family']} | {comparison['pair_id']} | {routes} | {comparison['lowest_credit_accepted_route'] or 'NA'} | {comparison['lowest_credit_clean_route'] or 'NA'} |")
    lines.extend(["", "## Calibration recommendations", ""])
    lines.extend(f"- {note}" for note in document["recommendations"])
    lines.extend(["", "## Caveats", "", "- Acceptance, rework, defects, and quality come only from the explicit ledger; they are never inferred from `task_complete`.",
                  "- Session duration is first-to-last recorded activity and may include waiting, scheduler delay, or user idle time; it is not pure model compute time.",
                  "- `Lowest-credit accepted` is descriptive and may include rework or defects. Use the clean field plus repeated matched evidence for routing decisions.",
                  "- Compare equivalent task families, repository revisions, prompts, tools, and rubrics. Observational route averages are confounded by task difficulty.",
                  "- Require repeated matched trials before changing a global route. Higher effort may improve quality while using more tokens.", ""])
    return "\n".join(lines)


def load_rate_card(path: Path | None) -> dict[str, Any]:
    if not path:
        return DEFAULT_RATE_CARD
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AUDIT.AuditError(f"Invalid rate card: {exc}") from exc
    if not isinstance(value, dict) or not isinstance(value.get("credits_per_million"), dict):
        raise AUDIT.AuditError("Rate card needs credits_per_million")
    for model, rates in value["credits_per_million"].items():
        if not isinstance(model, str) or not isinstance(rates, dict):
            raise AUDIT.AuditError("Rate card model entries must be objects")
        for field in ("input", "cached_input", "output"):
            rate = rates.get(field)
            if isinstance(rate, bool) or not isinstance(rate, (int, float)) or rate < 0:
                raise AUDIT.AuditError(f"Rate card {model}.{field} must be a non-negative number")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", nargs="?", help="root task UUID")
    parser.add_argument("--current", action="store_true")
    parser.add_argument("--codex-home", type=Path, default=AUDIT.default_codex_home())
    parser.add_argument("--state-db", type=Path)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--rate-card", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--markdown-out", type=Path)
    parser.add_argument("--init-ledger", type=Path)
    parser.add_argument("--include-identifiers", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.current and args.task:
        parser.error("Use --current or a task UUID, not both")
    root_id = os.environ.get("CODEX_THREAD_ID") if args.current else args.task
    if not root_id or not AUDIT.parse_task_id(root_id):
        parser.error("Provide a root task UUID or use --current with CODEX_THREAD_ID")
    root_id = AUDIT.parse_task_id(root_id)
    state_db = (args.state_db or (args.codex_home / "state_5.sqlite")).expanduser().resolve()
    try:
        ledger = load_ledger(args.ledger)
        rate_card = load_rate_card(args.rate_card)
        runs, protected = make_runs(root_id, state_db, args.include_identifiers, ledger, rate_card)
        protected.update(path.expanduser().resolve() for path in
                         (args.ledger, args.baseline, args.rate_card) if path)
        apply_baseline(runs, args.baseline)
        document = {"schema_version": 1, "redacted": not args.include_identifiers,
                    "recommendation_only": True, "root_ref": ref(root_id, args.include_identifiers),
                    "rate_card": rate_card, "runs": runs, "cohorts": build_cohorts(runs),
                    "paired_comparisons": build_pairs(runs)}
        document["recommendations"] = recommendations(document["paired_comparisons"])
        rendered_json = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
        rendered_md = markdown(document)
        outputs = [path.expanduser().resolve() for path in
                   (args.json_out, args.markdown_out, args.init_ledger) if path]
        if len(outputs) != len(set(outputs)):
            raise AUDIT.AuditError("JSON, Markdown, and ledger outputs must use different paths")
        if args.json_out:
            AUDIT.safe_write(args.json_out, rendered_json, protected, args.force)
        if args.markdown_out:
            AUDIT.safe_write(args.markdown_out, rendered_md, protected, args.force)
        if args.init_ledger:
            AUDIT.safe_write(args.init_ledger, json.dumps(ledger_template(runs), indent=2) + "\n", protected, args.force)
        print(rendered_md)
    except AUDIT.AuditError as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    main()
