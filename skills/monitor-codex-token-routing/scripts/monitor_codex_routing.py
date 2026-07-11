#!/usr/bin/env python3
"""Continuously refresh advisory Codex routing telemetry."""
from __future__ import annotations

import argparse, importlib.util, json, os, signal, sys, time
from datetime import datetime, timezone
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAL_PATH = HERE.parents[1] / "audit-codex-token-routing" / "scripts" / "calibrate_codex_routing.py"
SPEC = importlib.util.spec_from_file_location("codex_calibration", CAL_PATH)
CAL = importlib.util.module_from_spec(SPEC); assert SPEC.loader; SPEC.loader.exec_module(CAL)
STOP = False

def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)

def compact(document: dict) -> dict:
    runs = document["runs"]
    total_tokens = sum(int(r.get("gross_total_tokens", 0)) for r in runs)
    credits = round(sum(float(r.get("estimated_credits") or 0) for r in runs), 4)
    coordination = sum(int(r.get("coordination_tokens_approx", 0)) for r in runs)
    compactions = sum(int(r.get("compactions", 0)) for r in runs)
    open_links = sum(r.get("edge_status") == "open" for r in runs if r.get("depth", 0) > 0)
    assessed = [r for r in runs if r.get("outcome") != "not_assessed"]
    alerts = []
    if total_tokens and coordination / total_tokens >= .20:
        alerts.append(f"Coordination is approximately {coordination / total_tokens:.0%} of observed tokens.")
    high_pressure = [r for r in runs if isinstance(r.get("latest_context_pressure"), (int, float)) and r["latest_context_pressure"] >= .75]
    if high_pressure: alerts.append(f"{len(high_pressure)} agent(s) are at or above 75% context pressure.")
    if open_links >= 4: alerts.append(f"{open_links} durable child links remain open; verify live agent state before more fan-out.")
    recs = list(document.get("recommendations", []))[:3]
    return {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
            "recommendation_only": True, "root_ref": document.get("root_ref"),
            "health": "warning" if alerts else "ok", "open_child_links": open_links,
            "observed_agents": len(runs), "assessed_agents": len(assessed),
            "gross_tokens": total_tokens, "estimated_credits": credits,
            "coordination_tokens_approx": coordination, "compactions": compactions,
            "alerts": alerts, "recommended_actions": recs}

def html_dashboard(doc: dict, snapshot: dict, refresh: int) -> str:
    routes = {}
    for run in doc["runs"]:
        route = run["route"]; routes.setdefault(route, {"tokens":0,"credits":0,"runs":0})
        routes[route]["tokens"] += run["gross_total_tokens"]; routes[route]["credits"] += float(run.get("estimated_credits") or 0); routes[route]["runs"] += 1
    max_tokens = max([v["tokens"] for v in routes.values()] or [1])
    bars = "".join(f'<tr><td>{escape(k)}</td><td>{v["runs"]}</td><td>{v["tokens"]:,}</td><td>{v["credits"]:.3f}</td><td><div class="bar" style="width:{max(2,v["tokens"]/max_tokens*100):.1f}%"></div></td></tr>' for k,v in sorted(routes.items()))
    alerts = "".join(f"<li>{escape(x)}</li>" for x in snapshot["alerts"]) or "<li>No automatic warning threshold crossed.</li>"
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="refresh" content="{refresh}"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Codex routing monitor</title><style>body{{font:16px system-ui;margin:2rem;max-width:1100px;background:#0d1117;color:#e6edf3}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}}.card{{background:#161b22;padding:16px;border:1px solid #30363d;border-radius:8px}}table{{width:100%;border-collapse:collapse;margin-top:1rem}}th,td{{padding:9px;border-bottom:1px solid #30363d;text-align:left}}.bar{{height:12px;background:#3fb950;border-radius:6px}}small{{color:#8b949e}}</style></head><body><h1>Codex routing monitor</h1><small>Advisory, redacted, refreshed {escape(snapshot["generated_at"])}</small><div class="cards"><div class="card"><b>Health</b><br>{snapshot["health"]}</div><div class="card"><b>Agents</b><br>{snapshot["observed_agents"]} observed / {snapshot["open_child_links"]} open links</div><div class="card"><b>Gross tokens</b><br>{snapshot["gross_tokens"]:,}</div><div class="card"><b>Estimated credits</b><br>{snapshot["estimated_credits"]:.3f}</div></div><h2>Signals</h2><ul>{alerts}</ul><h2>Usage by route</h2><table><thead><tr><th>Route</th><th>Runs</th><th>Tokens</th><th>Credits</th><th>Relative tokens</th></tr></thead><tbody>{bars}</tbody></table><h2>Recommendations</h2><ul>{''.join(f'<li>{escape(x)}</li>' for x in snapshot['recommended_actions'])}</ul></body></html>'''

def collect(args) -> tuple[dict, dict]:
    root = os.environ.get("CODEX_THREAD_ID") if args.current else args.task
    if not root or not CAL.AUDIT.parse_task_id(root): raise CAL.AUDIT.AuditError("Provide a task UUID or use --current with CODEX_THREAD_ID")
    root = CAL.AUDIT.parse_task_id(root)
    state = (args.state_db or args.codex_home / "state_5.sqlite").expanduser().resolve()
    ledger = CAL.load_ledger(args.ledger); rates = CAL.load_rate_card(args.rate_card)
    runs, _ = CAL.make_runs(root, state, False, ledger, rates)
    doc = {"schema_version":1,"redacted":True,"recommendation_only":True,"root_ref":CAL.ref(root,False),"rate_card":rates,"runs":runs,"cohorts":CAL.build_cohorts(runs),"paired_comparisons":CAL.build_pairs(runs)}
    doc["recommendations"] = CAL.recommendations(doc["paired_comparisons"])
    return doc, compact(doc)

def write_cycle(args, generation: int) -> None:
    doc, snap = collect(args); out = args.output_dir.resolve()
    atomic_write(out/"calibration.json", json.dumps(doc,indent=2)+"\n")
    atomic_write(out/"current-agent.json", json.dumps(snap,indent=2)+"\n")
    atomic_write(out/"current-report.md", CAL.markdown(doc))
    atomic_write(out/"dashboard.html", html_dashboard(doc,snap,max(5,args.interval)))
    atomic_write(out/"monitor-status.json", json.dumps({"status":"running" if not args.once else "complete","generation":generation,"last_success":snap["generated_at"],"last_error":None},indent=2)+"\n")

def main() -> None:
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("task",nargs="?"); p.add_argument("--current",action="store_true"); p.add_argument("--codex-home",type=Path,default=CAL.AUDIT.default_codex_home()); p.add_argument("--state-db",type=Path); p.add_argument("--ledger",type=Path); p.add_argument("--rate-card",type=Path); p.add_argument("--output-dir",type=Path,required=True); p.add_argument("--interval",type=int,default=30); p.add_argument("--once",action="store_true"); args=p.parse_args()
    if args.current and args.task: p.error("Use --current or a task UUID, not both")
    if args.interval < 5: p.error("--interval must be at least 5 seconds")
    global STOP
    def stop(*_):
        global STOP; STOP=True
    signal.signal(signal.SIGINT,stop); signal.signal(signal.SIGTERM,stop)
    generation=0
    while not STOP:
        generation += 1
        try: write_cycle(args,generation)
        except Exception as exc:
            atomic_write(args.output_dir.resolve()/"monitor-status.json",json.dumps({"status":"error","generation":generation,"last_error":str(exc)},indent=2)+"\n")
            if args.once: p.exit(2,f"error: {exc}\n")
        if args.once: break
        end=time.monotonic()+args.interval
        while not STOP and time.monotonic()<end: time.sleep(min(.5,end-time.monotonic()))
    if STOP:
        atomic_write(args.output_dir.resolve()/"monitor-status.json",json.dumps({"status":"stopped","generation":generation,"last_error":None},indent=2)+"\n")

if __name__=="__main__": main()
