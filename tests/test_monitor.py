import importlib.util
import json
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "monitor-codex-token-routing" / "scripts" / "monitor_codex_routing.py"
SPEC = importlib.util.spec_from_file_location("monitor", SCRIPT)
MON = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MON)


def document():
    return {
        "root_ref": "redacted:root",
        "runs": [
            {"depth": 0, "route": "gpt-5.6-sol/high", "gross_total_tokens": 1000,
             "estimated_credits": 1.0, "coordination_tokens_approx": 100,
             "compactions": 1, "edge_status": "root", "outcome": "not_assessed",
             "latest_context_pressure": .2},
            {"depth": 1, "route": "gpt-5.6-luna/high", "gross_total_tokens": 1000,
             "estimated_credits": .2, "coordination_tokens_approx": 400,
             "compactions": 0, "edge_status": "open", "outcome": "accepted",
             "latest_context_pressure": .8},
        ],
        "recommendations": ["Repeat the matched trial."],
    }


class MonitorTests(unittest.TestCase):
    def test_compact_snapshot_is_small_and_advisory(self):
        snap = MON.compact(document())
        self.assertTrue(snap["recommendation_only"])
        self.assertEqual(snap["gross_tokens"], 2000)
        self.assertEqual(snap["open_child_links"], 1)
        self.assertEqual(snap["assessed_agents"], 1)
        self.assertEqual(snap["health"], "warning")
        self.assertIn("comparison_status", snap)
        self.assertIn("working_hypothesis", snap)
        self.assertIn("next_test", snap)
        self.assertNotIn("runs", snap)
        self.assertLess(len(json.dumps(snap)), 2000)

    def test_dashboard_has_charts_and_no_script_or_server(self):
        snap = MON.compact(document())
        page = MON.html_dashboard(document(), snap, 30)
        self.assertIn('http-equiv="refresh"', page)
        self.assertIn("Usage by route", page)
        self.assertIn("gpt-5.6-luna/high", page)
        self.assertNotIn("<script", page.lower())
        self.assertNotIn("redacted:root", page)

    def test_atomic_write_replaces_and_leaves_no_temp(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "current-agent.json"
            MON.atomic_write(path, "one")
            MON.atomic_write(path, "two")
            self.assertEqual(path.read_text(), "two")
            self.assertFalse(path.with_name(path.name + ".tmp").exists())

    def test_refresh_failure_preserves_artifacts_and_records_error(self):
        with tempfile.TemporaryDirectory() as td:
            output = Path(td)
            report = output / "current-report.md"
            dashboard = output / "dashboard.html"
            report.write_text("last good report", encoding="utf-8")
            dashboard.write_text("last good dashboard", encoding="utf-8")
            argv = ["monitor_codex_routing.py", "--current", "--output-dir", str(output), "--once"]
            with patch.object(MON, "collect", side_effect=MON.CAL.AUDIT.AuditError("simulated refresh failure")):
                with patch.object(sys, "argv", argv):
                    with self.assertRaises(SystemExit) as raised:
                        MON.main()
            self.assertEqual(raised.exception.code, 2)
            self.assertEqual(report.read_text(encoding="utf-8"), "last good report")
            self.assertEqual(dashboard.read_text(encoding="utf-8"), "last good dashboard")
            status = json.loads((output / "monitor-status.json").read_text(encoding="utf-8"))
            self.assertEqual(status["status"], "error")
            self.assertIn("simulated refresh failure", status["last_error"])

    def test_monitor_rejects_output_collision_with_input(self):
        with tempfile.TemporaryDirectory() as td:
            output = Path(td)
            args = SimpleNamespace(output_dir=output, interval=30, once=True)
            protected = {output.resolve() / "current-agent.json"}
            with patch.object(MON, "collect", return_value=(document(), MON.compact(document()), protected)):
                with self.assertRaises(MON.CAL.AUDIT.AuditError):
                    MON.write_cycle(args, 1)
            self.assertFalse((output / "current-agent.json").exists())


if __name__ == "__main__":
    unittest.main()
