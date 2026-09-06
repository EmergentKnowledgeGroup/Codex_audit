import json
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).parents[1] / "skills/audit-codex-token-routing/scripts"
sys.path.insert(0, str(SCRIPTS))
import audit_usage_window as W  # noqa: E402
import render_usage_report as R  # noqa: E402


class WindowTests(unittest.TestCase):
    def parse(self, records):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "session.jsonl"
            path.write_text("\n".join(json.dumps(x) for x in records), encoding="utf8")
            coverage = Counter()
            es, _, _ = W.parse_session(path, "root", W.stamp("2026-09-05T00:00:00Z"), W.stamp("2026-09-06T00:00:00Z"), coverage)
            return es, coverage

    @staticmethod
    def record(outer, payload, time="2026-09-05T01:00:00Z"):
        return {"timestamp": time, "type": outer, "payload": payload}

    def test_window_dedup_and_model_switch(self):
        u = dict(input_tokens=100, cached_input_tokens=80, output_tokens=10, reasoning_output_tokens=2, total_tokens=110)
        def ctx(model, turn):
            return self.record("turn_context", {"model": model, "effort": "low", "turn_id": turn})
        def event(turn, rid, time):
            return self.record("token_usage_record", {"thread_id": "root", "turn_id": turn, "response_id": rid, "usage": u}, time)
        notification = self.record("event_msg", {"type": "token_count", "info": {"total_token_usage": u, "last_token_usage": u}})
        records = [ctx("gpt-6-astra", "a"), event("a", "before", "2026-09-04T23:59:59Z"),
                   event("a", "one", "2026-09-05T00:00:00Z"), notification, notification,
                   ctx("gpt-5.6-luna", "b"), event("b", "two", "2026-09-05T02:00:00Z"),
                   event("b", "after", "2026-09-06T00:00:00Z")]
        es, cov = self.parse(records)
        self.assertEqual([x["model"] for x in es], ["gpt-6-astra", "gpt-5.6-luna"])
        self.assertEqual(sum(x["total_tokens"] for x in es), 220)
        self.assertEqual(cov["duplicate_cumulative_notifications"], 1)
        self.assertEqual(cov["legacy_fallback_records"], 0)

    def test_legacy_turn_survives_modern_later_turn(self):
        u = dict(input_tokens=100, cached_input_tokens=80, output_tokens=10, total_tokens=110)
        es, _ = self.parse([
            self.record("turn_context", {"turn_id": "old", "model": "gpt-5.6-sol"}),
            self.record("event_msg", {"type": "token_count", "info": {"total_token_usage": u, "last_token_usage": u}}),
            self.record("turn_context", {"turn_id": "new", "model": "gpt-6-astra"}),
            self.record("token_usage_record", {"thread_id": "root", "turn_id": "new", "usage": u}),
        ])
        self.assertEqual(len(es), 2)

    def test_foreign_child_history_excluded(self):
        es, cov = self.parse([self.record("token_usage_record", {"thread_id": "parent", "usage": {"total_tokens": 999}})])
        self.assertEqual(es, [])
        self.assertEqual(cov["foreign_usage_records_skipped"], 1)

    def test_after_cutoff_cannot_suppress_in_window_fallback(self):
        u = dict(input_tokens=100, cached_input_tokens=80, output_tokens=10, total_tokens=110)
        records = [self.record("turn_context", {"turn_id": "live", "model": "gpt-6-astra"}),
                   self.record("event_msg", {"type": "token_count", "info": {"total_token_usage": u, "last_token_usage": u}})]
        before, _ = self.parse(records)
        records.append(self.record("token_usage_record", {"thread_id": "root", "turn_id": "live", "usage": u}, "2026-09-06T00:00:01Z"))
        after, _ = self.parse(records)
        self.assertEqual(before, after)

    def test_pricing_subsets_and_unknown(self):
        u = dict(input_tokens=1_000_000, cached_input_tokens=800_000, output_tokens=10_000, reasoning_output_tokens=5000)
        self.assertEqual(W.credits(u, "gpt-6-astra"), 82.5)
        self.assertEqual(W.credits(u, "gpt-5.6-sol"), 33)
        self.assertIsNone(W.credits(u, "future-model"))

    def test_offset_and_render_privacy(self):
        self.assertEqual(W.stamp("2026-09-04T19:00:00-05:00"), W.stamp("2026-09-05T00:00:00Z"))
        with self.assertRaises(ValueError):
            W.stamp("2026-09-05T00:00:00")
        doc = {"chats": [{"title": "<script>alert(1)</script>", "task_ref": "redacted:abc"}]}
        self.assertNotIn("<script>alert", R.render_html(doc))
        self.assertIn("redacted:abc", R.render_html(doc))


if __name__ == "__main__":
    unittest.main()
