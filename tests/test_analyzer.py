import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "skills" / "audit-codex-token-routing" / "scripts" / "analyze_codex_tokens.py"
SPEC = importlib.util.spec_from_file_location("analyze_codex_tokens", SCRIPT)
ANALYZER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(ANALYZER)
TASK = "11111111-2222-3333-4444-555555555555"


def write_fixture(root: Path, malformed: bool = False):
    session_dir = root / "sessions" / "2026" / "07" / "09"
    session_dir.mkdir(parents=True)
    session = session_dir / f"rollout-2026-07-09T00-00-00-{TASK}.jsonl"
    records = [
        {"type": "turn_context", "payload": {"model": "gpt-5.6-sol", "effort": "high"}},
        {"type": "event_msg", "payload": {"type": "task_started"}},
        {"type": "event_msg", "payload": {"type": "token_count", "info": {
            "total_token_usage": {"input_tokens": 100, "cached_input_tokens": 80, "output_tokens": 5,
                                  "reasoning_output_tokens": 2, "total_tokens": 105},
            "last_token_usage": {"input_tokens": 100, "cached_input_tokens": 80, "output_tokens": 5,
                                 "reasoning_output_tokens": 2, "total_tokens": 105},
            "model_context_window": 1000}}},
        {"type": "response_item", "payload": {"type": "function_call", "name": "spawn_agent",
          "call_id": "a", "arguments": json.dumps({"model": "gpt-5.6-terra", "reasoning_effort": "high", "fork_turns": "none"})}},
        {"type": "response_item", "payload": {"type": "function_call_output", "call_id": "a", "output": "ok"}},
        {"type": "event_msg", "payload": {"type": "context_compacted"}},
        {"type": "event_msg", "payload": {"type": "task_complete"}},
    ]
    with session.open("w", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record) + "\n")
        if malformed:
            stream.write("{partial\n")

    db = root / "state_5.sqlite"
    conn = sqlite3.connect(db)
    try:
        conn.executescript("""
        CREATE TABLE threads(id TEXT PRIMARY KEY,title TEXT,cwd TEXT,model TEXT,reasoning_effort TEXT,tokens_used INTEGER,created_at INTEGER,updated_at INTEGER);
        CREATE TABLE thread_spawn_edges(parent_thread_id TEXT,child_thread_id TEXT PRIMARY KEY,status TEXT);
        """)
        conn.execute("INSERT INTO threads VALUES(?,?,?,?,?,?,?,?)",
                     (TASK, "private title", "Z:/private", "gpt-5.6-sol", "high", 105, 1, 2))
        child = "11111111-2222-3333-4444-555555555556"
        conn.execute("INSERT INTO threads VALUES(?,?,?,?,?,?,?,?)",
                     (child, "child", "Z:/private", "gpt-5.6-terra", "high", 50, 1, 2))
        conn.execute("INSERT INTO thread_spawn_edges VALUES(?,?,?)", (TASK, child, "open"))
        grandchild = "11111111-2222-3333-4444-555555555557"
        conn.execute("INSERT INTO threads VALUES(?,?,?,?,?,?,?,?)",
                     (grandchild, "grandchild", "Z:/private", "gpt-5.6-luna", "medium", 25, 1, 2))
        conn.execute("INSERT INTO thread_spawn_edges VALUES(?,?,?)", (child, grandchild, "open"))
        conn.commit()
    finally:
        conn.close()
    return session, db


class AnalyzerTests(unittest.TestCase):
    def test_redaction_default_and_child_rollup(self):
        with tempfile.TemporaryDirectory() as tmp:
            session, db = write_fixture(Path(tmp))
            report = ANALYZER.analyze(session, TASK, db, False, False)
            self.assertTrue(report["task_ref"].startswith("redacted:"))
            self.assertNotIn("session_path", report)
            self.assertNotIn("title", report["state_metadata"])
            self.assertEqual(report["child_metadata"]["direct_child_tokens"], 50)
            self.assertEqual(report["child_metadata"]["descendant_tokens"], 75)
            self.assertEqual(report["child_metadata"]["all_descendants"], 2)
            self.assertEqual(report["latest_context_pressure"], 0.1)

    def test_identifier_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            session, db = write_fixture(Path(tmp))
            report = ANALYZER.analyze(session, TASK, db, True, False)
            self.assertEqual(report["task_ref"], TASK)
            self.assertEqual(report["state_metadata"]["title"], "private title")
            self.assertEqual(report["session_path"], str(session))

    def test_malformed_line_fails_or_skips(self):
        with tempfile.TemporaryDirectory() as tmp:
            session, db = write_fixture(Path(tmp), malformed=True)
            with self.assertRaises(ANALYZER.AuditError):
                ANALYZER.analyze(session, TASK, db, False, False)
            report = ANALYZER.analyze(session, TASK, db, False, True)
            self.assertEqual(report["invalid_jsonl_lines_skipped"], 1)

    def test_safe_write_protects_inputs_and_existing_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.jsonl"
            path.write_text("x", encoding="utf-8")
            with self.assertRaises(ANALYZER.AuditError):
                ANALYZER.safe_write(path, "report", {path.resolve()}, False)
            output = Path(tmp) / "report.json"
            ANALYZER.safe_write(output, "first", {path.resolve()}, False)
            with self.assertRaises(ANALYZER.AuditError):
                ANALYZER.safe_write(output, "second", set(), False)
            ANALYZER.safe_write(output, "second", set(), True)
            self.assertEqual(output.read_text(encoding="utf-8"), "second")

    def test_current_uses_environment_thread_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_fixture(root)
            env = os.environ.copy()
            env["CODEX_THREAD_ID"] = TASK
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--current", "--codex-home", str(root)],
                text=True, capture_output=True, env=env, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            document = json.loads(result.stdout)
            self.assertTrue(document["redacted"])
            self.assertEqual(len(document["reports"]), 1)


if __name__ == "__main__":
    unittest.main()
