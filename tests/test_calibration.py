import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "skills" / "audit-codex-token-routing" / "scripts" / "calibrate_codex_routing.py"
SPEC = importlib.util.spec_from_file_location("calibrate_codex_routing", SCRIPT)
CAL = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(CAL)

ROOT_ID = "aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb"
LUNA_ID = "aaaaaaaa-1111-2222-3333-bbbbbbbbbbbc"
TERRA_ID = "aaaaaaaa-1111-2222-3333-bbbbbbbbbbbd"


def write_session(path: Path, model: str, effort: str, usage: dict, turns: int = 1):
    records = [{"timestamp": "2026-01-01T00:00:00Z", "type": "turn_context",
                "payload": {"model": model, "effort": effort}}]
    for index in range(turns):
        records.extend([
            {"timestamp": f"2026-01-01T00:00:0{index + 1}Z", "type": "event_msg",
             "payload": {"type": "task_started"}},
            {"timestamp": f"2026-01-01T00:00:0{index + 2}Z", "type": "event_msg",
             "payload": {"type": "token_count", "info": {
                 "total_token_usage": usage, "last_token_usage": usage,
                 "model_context_window": 10000}}},
            {"timestamp": f"2026-01-01T00:00:0{index + 3}Z", "type": "response_item",
             "payload": {"type": "message", "role": "assistant", "content": []}},
            {"timestamp": f"2026-01-01T00:00:0{index + 4}Z", "type": "event_msg",
             "payload": {"type": "task_complete"}},
        ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")


def fixture(root: Path):
    sessions = root / "sessions"
    root_path = sessions / f"root-{ROOT_ID}.jsonl"
    luna_path = sessions / f"luna-{LUNA_ID}.jsonl"
    terra_path = sessions / f"terra-{TERRA_ID}.jsonl"
    write_session(root_path, "gpt-5.6-sol", "high",
                  {"input_tokens": 100, "cached_input_tokens": 80, "output_tokens": 10,
                   "reasoning_output_tokens": 2, "total_tokens": 110})
    write_session(luna_path, "gpt-5.6-luna", "high",
                  {"input_tokens": 1000, "cached_input_tokens": 800, "output_tokens": 100,
                   "reasoning_output_tokens": 20, "total_tokens": 1100}, turns=2)
    write_session(terra_path, "gpt-5.6-terra", "medium",
                  {"input_tokens": 400, "cached_input_tokens": 300, "output_tokens": 50,
                   "reasoning_output_tokens": 10, "total_tokens": 450})
    db = root / "state_5.sqlite"
    conn = sqlite3.connect(db)
    try:
        conn.executescript("""
        CREATE TABLE threads(id TEXT PRIMARY KEY,rollout_path TEXT,model TEXT,reasoning_effort TEXT,tokens_used INTEGER,created_at INTEGER,updated_at INTEGER,created_at_ms INTEGER,updated_at_ms INTEGER,agent_path TEXT);
        CREATE TABLE thread_spawn_edges(parent_thread_id TEXT,child_thread_id TEXT PRIMARY KEY,status TEXT);
        """)
        conn.executemany("INSERT INTO threads VALUES(?,?,?,?,?,?,?,?,?,?)", [
            (ROOT_ID, str(root_path), "gpt-5.6-sol", "high", 110, 1, 4, 1000, 4000, "/root"),
            (LUNA_ID, str(luna_path), "gpt-5.6-luna", "high", 1100, 1, 8, 1000, 8000, "/root/luna"),
            (TERRA_ID, str(terra_path), "gpt-5.6-terra", "medium", 450, 1, 4, 1000, 4000, "/root/terra"),
        ])
        conn.executemany("INSERT INTO thread_spawn_edges VALUES(?,?,?)", [
            (ROOT_ID, LUNA_ID, "closed"), (ROOT_ID, TERRA_ID, "closed")])
        conn.commit()
    finally:
        conn.close()
    return db


class CalibrationTests(unittest.TestCase):
    def test_gpt_56_alias_uses_sol_rate(self):
        usage = {"input_tokens": 1000, "cached_input_tokens": 0, "output_tokens": 0}
        self.assertEqual(CAL.credit_estimate(usage, "gpt-5.6", CAL.DEFAULT_RATE_CARD), 0.125)

    def test_tree_metrics_ledger_and_pair_recommendation(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = fixture(Path(tmp))
            ledger = {
                CAL.ref(LUNA_ID, False): {"task_family": "small-edit", "pair_id": "p1",
                                          "outcome": "accepted", "rework_rounds": 1, "defects": 0},
                CAL.ref(TERRA_ID, False): {"task_family": "small-edit", "pair_id": "p1",
                                           "outcome": "accepted", "rework_rounds": 0, "defects": 0},
            }
            runs, _ = CAL.make_runs(ROOT_ID, db, False, ledger, CAL.DEFAULT_RATE_CARD)
            self.assertEqual(len(runs), 3)
            luna = next(run for run in runs if run["route"] == "gpt-5.6-luna/high")
            self.assertEqual(luna["additional_task_turns_proxy"], 1)
            self.assertIsNotNone(luna["estimated_credits"])
            pairs = CAL.build_pairs(runs)
            self.assertEqual(len(pairs), 1)
            notes = CAL.recommendations(pairs)
            self.assertTrue(any("zero recorded rework/defects" in note for note in notes))
            self.assertEqual(pairs[0]["lowest_credit_clean_route"], "gpt-5.6-terra/medium")

    def test_invalid_ledger_and_rate_card_are_controlled_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = root / "ledger.json"
            ledger.write_text(json.dumps({"evaluations": [{"task_ref": "x", "outcome": "accepted", "rework_rounds": "many"}]}), encoding="utf-8")
            with self.assertRaises(CAL.AUDIT.AuditError):
                CAL.load_ledger(ledger)
            rate = root / "rates.json"
            rate.write_text(json.dumps({"credits_per_million": {"gpt-5.6-luna": {"input": "cheap"}}}), encoding="utf-8")
            with self.assertRaises(CAL.AUDIT.AuditError):
                CAL.load_rate_card(rate)

    def test_no_ledger_never_infers_acceptance(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = fixture(Path(tmp))
            runs, _ = CAL.make_runs(ROOT_ID, db, False, {}, CAL.DEFAULT_RATE_CARD)
            self.assertTrue(all(run["outcome"] == "not_assessed" for run in runs))
            self.assertEqual(CAL.build_pairs(runs), [])

    def test_ledger_template_excludes_root_and_redacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = fixture(Path(tmp))
            runs, _ = CAL.make_runs(ROOT_ID, db, False, {}, CAL.DEFAULT_RATE_CARD)
            template = CAL.ledger_template(runs)
            self.assertEqual(len(template["evaluations"]), 2)
            self.assertTrue(all(item["task_ref"].startswith("redacted:") for item in template["evaluations"]))
            self.assertTrue(all(item["observed_route"] for item in template["evaluations"]))

    def test_markdown_is_readable_and_caveated(self):
        document = {"runs": [], "paired_comparisons": [], "cohorts": [],
                    "recommendations": ["Collect matched trials."],
                    "rate_card": CAL.DEFAULT_RATE_CARD}
        output = CAL.markdown(document)
        self.assertIn("# Codex routing calibration", output)
        self.assertIn("never inferred", output)


if __name__ == "__main__":
    unittest.main()
