import importlib.util
import json
import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
