#!/usr/bin/env python3
"""Read-only analyzer for local Codex task token and subagent usage."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import statistics
import tempfile
from collections import Counter, defaultdict
from contextlib import closing
from pathlib import Path
from typing import Any


UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
USAGE_FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens", "total_tokens")


class AuditError(RuntimeError):
    pass


def default_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))


def parse_task_id(value: str) -> str | None:
    match = UUID_RE.search(value)
    return match.group(0).lower() if match else None


def find_session(selector: str, codex_home: Path) -> tuple[Path, str]:
    candidate = Path(selector).expanduser()
    if candidate.is_file():
        task_id = parse_task_id(candidate.name)
        if not task_id:
            raise AuditError(f"Session filename does not contain a task UUID: {candidate}")
        return candidate.resolve(), task_id
    task_id = parse_task_id(selector)
    if not task_id:
        raise AuditError(f"Expected a Codex task UUID or JSONL path, got: {selector!r}")
    root = codex_home / "sessions"
    matches = list(root.glob(f"**/*{task_id}*.jsonl")) if root.exists() else []
    if len(matches) != 1:
        raise AuditError(f"Expected one session for {task_id}; found {len(matches)} under {root}")
    return matches[0].resolve(), task_id


def readonly_connection(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)


def table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in conn.execute(f"PRAGMA table_info({table})")}


def load_state(task_id: str, state_db: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    metadata: dict[str, Any] = {"status": "unavailable"}
    children: dict[str, Any] = {"status": "unavailable", "direct_children": 0,
                                "direct_child_tokens": 0, "all_descendants": 0,
                                "descendant_tokens": 0, "direct_routes": [],
                                "descendant_routes": []}
    if not state_db.exists():
        return metadata, children
    try:
        with closing(readonly_connection(state_db)) as conn:
            thread_cols = table_columns(conn, "threads")
            required = {"id", "model", "reasoning_effort", "tokens_used"}
            if not required.issubset(thread_cols):
                return {"status": "schema_mismatch", "missing_columns": sorted(required - thread_cols)}, children
            optional = [name for name in ("title", "cwd", "created_at", "updated_at") if name in thread_cols]
            names = ["model", "reasoning_effort", "tokens_used", *optional]
            row = conn.execute(f"SELECT {','.join(names)} FROM threads WHERE id=?", (task_id,)).fetchone()
            metadata = {"status": "ok" if row else "not_found"}
            if row:
                metadata.update(dict(zip(names, row)))

            edge_cols = table_columns(conn, "thread_spawn_edges")
            if not {"parent_thread_id", "child_thread_id"}.issubset(edge_cols):
                children["status"] = "schema_mismatch"
                return metadata, children
            direct_rows = conn.execute(
                "SELECT COALESCE(t.model,'unknown'),COALESCE(t.reasoning_effort,'unknown'),"
                "COUNT(*),COALESCE(SUM(t.tokens_used),0),COALESCE(MIN(t.tokens_used),0),"
                "COALESCE(CAST(AVG(t.tokens_used) AS INT),0),COALESCE(MAX(t.tokens_used),0) "
                "FROM thread_spawn_edges e JOIN threads t ON t.id=e.child_thread_id "
                "WHERE e.parent_thread_id=? GROUP BY t.model,t.reasoning_effort",
                (task_id,),
            ).fetchall()
            descendant_rows = conn.execute(
                "WITH RECURSIVE descendants(id) AS ("
                "SELECT child_thread_id FROM thread_spawn_edges WHERE parent_thread_id=? "
                "UNION SELECT e.child_thread_id FROM thread_spawn_edges e "
                "JOIN descendants d ON e.parent_thread_id=d.id) "
                "SELECT COALESCE(t.model,'unknown'),COALESCE(t.reasoning_effort,'unknown'),"
                "COUNT(*),COALESCE(SUM(t.tokens_used),0),COALESCE(MIN(t.tokens_used),0),"
                "COALESCE(CAST(AVG(t.tokens_used) AS INT),0),COALESCE(MAX(t.tokens_used),0) "
                "FROM descendants d JOIN threads t ON t.id=d.id GROUP BY t.model,t.reasoning_effort",
                (task_id,),
            ).fetchall()

            def route_rows(source: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
                result = [{
                "route": f"{model}/{effort}", "children": int(count), "tokens": int(tokens),
                "min_tokens": int(minimum), "avg_tokens": int(average), "max_tokens": int(maximum),
                } for model, effort, count, tokens, minimum, average, maximum in source]
                return sorted(result, key=lambda item: item["tokens"], reverse=True)

            direct_routes = route_rows(direct_rows)
            descendant_routes = route_rows(descendant_rows)
            children = {
                "status": "ok",
                "direct_children": sum(row["children"] for row in direct_routes),
                "direct_child_tokens": sum(row["tokens"] for row in direct_routes),
                "all_descendants": sum(row["children"] for row in descendant_routes),
                "descendant_tokens": sum(row["tokens"] for row in descendant_routes),
                "direct_routes": direct_routes,
                "descendant_routes": descendant_routes,
            }
    except (sqlite3.Error, OSError) as exc:
        metadata = {"status": "error", "error": type(exc).__name__}
        children = {"status": "error", "direct_children": 0, "direct_child_tokens": 0,
                    "all_descendants": 0, "descendant_tokens": 0,
                    "direct_routes": [], "descendant_routes": []}
    return metadata, children


def percentile(values: list[int], fraction: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[round((len(ordered) - 1) * fraction)]


def analyze(path: Path, task_id: str, state_db: Path, include_identifiers: bool, skip_invalid: bool) -> dict[str, Any]:
    totals: dict[str, int] = {}
    latest_usage: dict[str, int] = {}
    latest_window = 0
    usage_events: list[dict[str, int]] = []
    event_counts: Counter[str] = Counter()
    action_usage: dict[str, Counter[str]] = defaultdict(Counter)
    settings_usage: dict[str, Counter[str]] = defaultdict(Counter)
    tool_output_bytes: Counter[str] = Counter()
    spawn_routes: Counter[str] = Counter()
    spawn_forks: Counter[str] = Counter()
    spawn_types: Counter[str] = Counter()
    pending: dict[str, int] | None = None
    active_model = "unknown"
    active_effort = "unknown"
    call_names: dict[str, str] = {}
    invalid_lines = 0
    inter_agent_bytes = 0
    compact_events = 0
    compact_records = 0

    def attribute(name: str) -> None:
        nonlocal pending
        if pending:
            action_usage[name].update(pending)
            pending = None

    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                if skip_invalid:
                    invalid_lines += 1
                    continue
                raise AuditError(f"Invalid JSON in {path.name} at line {line_no}: {exc.msg}") from exc
            outer = str(obj.get("type", "unknown"))
            payload = obj.get("payload") or {}
            kind = str(payload.get("type", outer))
            event_counts[kind] += 1

            if outer == "turn_context":
                active_model = str(payload.get("model", active_model))
                active_effort = str(payload.get("effort", active_effort))
                settings = payload.get("collaboration_mode", {}).get("settings", {})
                active_model = str(settings.get("model", active_model))
                active_effort = str(settings.get("reasoning_effort", active_effort))
            elif kind == "thread_settings_applied":
                settings = payload.get("thread_settings", {})
                active_model = str(settings.get("model", active_model))
                active_effort = str(settings.get("reasoning_effort", active_effort))
            elif outer == "compacted":
                compact_records += 1
            elif kind == "context_compacted":
                compact_events += 1
            elif outer == "inter_agent_communication_metadata":
                inter_agent_bytes += len(line.encode("utf-8"))

            if kind == "token_count":
                attribute("unattributed")
                info = payload.get("info") or {}
                totals = info.get("total_token_usage") or totals
                latest_usage = info.get("last_token_usage") or {}
                latest_window = int(info.get("model_context_window") or latest_window or 0)
                pending = latest_usage or None
                if latest_usage:
                    usage_events.append(latest_usage)
                    settings_usage[f"{active_model}/{active_effort}"].update(latest_usage)
                continue

            if kind in ("function_call", "custom_tool_call"):
                name = str(payload.get("name") or kind)
                call_id = payload.get("call_id")
                if call_id:
                    call_names[str(call_id)] = name
                attribute(name)
                if name == "spawn_agent":
                    try:
                        arguments = json.loads(payload.get("arguments") or "{}")
                    except json.JSONDecodeError:
                        arguments = {}
                    spawn_routes[f"{arguments.get('model','<inherit>')}/{arguments.get('reasoning_effort','<inherit>')}"] += 1
                    spawn_forks[str(arguments.get("fork_turns", "<default>"))] += 1
                    spawn_types[str(arguments.get("agent_type", "<default>"))] += 1
                continue

            if kind in ("function_call_output", "custom_tool_call_output"):
                call_id = str(payload.get("call_id", ""))
                name = call_names.pop(call_id, "unknown")
                output = payload.get("output", payload.get("content", ""))
                tool_output_bytes[name] += len(str(output).encode("utf-8"))
                continue

            if kind == "message" and payload.get("role") == "assistant":
                attribute("assistant_message")

    attribute("unattributed")
    metadata, children = load_state(task_id, state_db)
    if not include_identifiers and metadata.get("status") == "ok":
        metadata = {key: value for key, value in metadata.items() if key in {"status", "model", "reasoning_effort", "tokens_used"}}

    gross: Counter[str] = Counter()
    for usage in usage_events:
        gross.update({key: int(usage.get(key, 0)) for key in USAGE_FIELDS})
    input_values = [int(item.get("input_tokens", 0)) for item in usage_events]
    input_total = int(totals.get("input_tokens", 0))
    cached = int(totals.get("cached_input_tokens", 0))
    latest_input = int(latest_usage.get("input_tokens", 0))

    def rows(source: dict[str, Counter[str]]) -> list[dict[str, Any]]:
        result = [{"name": name, **{key: int(value) for key, value in counts.items()}} for name, counts in source.items()]
        return sorted(result, key=lambda item: int(item.get("total_tokens", 0)), reverse=True)

    report: dict[str, Any] = {
        "task_ref": task_id if include_identifiers else "redacted:" + hashlib.sha256(task_id.encode()).hexdigest()[:12],
        "session_bytes": path.stat().st_size,
        "state_metadata": metadata,
        "child_metadata": children,
        "totals": totals,
        "gross_inference_usage": dict(gross),
        "gross_minus_final_tokens": int(gross.get("total_tokens", 0)) - int(totals.get("total_tokens", 0)),
        "cached_input_ratio": round(cached / input_total, 6) if input_total else 0,
        "latest_request_usage": latest_usage,
        "model_context_window": latest_window,
        "latest_context_pressure": round(latest_input / latest_window, 6) if latest_window else None,
        "model_inference_events": len(usage_events),
        "request_input_stats": {
            "min": min(input_values, default=0),
            "median": round(statistics.median(input_values)) if input_values else 0,
            "p90": percentile(input_values, .90), "p99": percentile(input_values, .99),
            "max": max(input_values, default=0),
        },
        "task_started": event_counts["task_started"],
        "task_complete": event_counts["task_complete"],
        "turn_aborted": event_counts["turn_aborted"],
        "compactions": max(compact_events, compact_records),
        "spawn_count": sum(spawn_routes.values()),
        "spawn_routes": dict(spawn_routes), "spawn_forks": dict(spawn_forks),
        "spawn_types": dict(spawn_types),
        "action_usage_approximate": rows(action_usage),
        "settings_usage_approximate": rows(settings_usage),
        "tool_output_bytes": dict(tool_output_bytes.most_common()),
        "inter_agent_metadata_bytes": inter_agent_bytes,
        "invalid_jsonl_lines_skipped": invalid_lines,
        "event_counts": dict(event_counts.most_common()),
    }
    if include_identifiers:
        report["session_path"] = str(path)
    return report


def safe_write(output: Path, text: str, protected: set[Path], force: bool) -> None:
    resolved = output.expanduser().resolve()
    if resolved in protected:
        raise AuditError(f"Refusing to overwrite audit input/state file: {resolved}")
    if resolved.exists() and not force:
        raise AuditError(f"Output exists; pass --force to replace it: {resolved}")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=resolved.name + ".", suffix=".tmp", dir=resolved.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        os.replace(temporary, resolved)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tasks", nargs="*", help="task UUIDs or session JSONL paths")
    parser.add_argument("--current", action="store_true", help="use CODEX_THREAD_ID")
    parser.add_argument("--codex-home", type=Path, default=default_codex_home())
    parser.add_argument("--state-db", type=Path)
    parser.add_argument("--include-identifiers", action="store_true")
    parser.add_argument("--skip-invalid", action="store_true", help="skip malformed/partial JSONL lines")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--force", action="store_true", help="replace an existing report")
    args = parser.parse_args()

    if args.current and args.tasks:
        parser.error("Use --current or task selectors, not both")
    selectors = list(args.tasks)
    if args.current:
        thread_id = os.environ.get("CODEX_THREAD_ID")
        if not thread_id:
            parser.error("CODEX_THREAD_ID is not set; provide a task UUID instead")
        selectors = [thread_id]
    if not selectors:
        parser.error("Provide at least one task UUID/path or use --current")

    state_db = (args.state_db or (args.codex_home / "state_5.sqlite")).expanduser().resolve()
    try:
        sessions = [find_session(selector, args.codex_home.expanduser()) for selector in selectors]
        reports = [analyze(path, task_id, state_db, args.include_identifiers, args.skip_invalid)
                   for path, task_id in sessions]
        document = {"schema_version": 1, "redacted": not args.include_identifiers,
                    "recommendation_only": True, "reports": reports}
        rendered = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
        if args.out:
            protected = {path for path, _ in sessions} | {state_db}
            safe_write(args.out, rendered, protected, args.force)
        print(rendered, end="")
    except AuditError as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    main()
