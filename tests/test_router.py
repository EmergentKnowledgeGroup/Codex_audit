import argparse
import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "skills" / "audit-codex-token-routing" / "scripts" / "route_task.py"
SPEC = importlib.util.spec_from_file_location("route_task", SCRIPT)
ROUTER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(ROUTER)


def args(**overrides):
    values = {
        "clarity": 1,
        "blast": 1,
        "judgment": 0,
        "validation": 2,
        "parallel_parts": 0,
        "max_children": 2,
        "repeatable": False,
        "shared_writes": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class RouterTests(unittest.TestCase):
    def test_clear_repeatable_isolated_uses_luna_medium(self):
        result = ROUTER.recommend(args(clarity=2, blast=0, repeatable=True))
        self.assertEqual((result["model"], result["reasoning_effort"]),
                         ("gpt-5.6-luna", "medium"))

    def test_cross_module_tradeoff_uses_terra_high(self):
        result = ROUTER.recommend(args(blast=2, judgment=1))
        self.assertEqual((result["model"], result["reasoning_effort"]),
                         ("gpt-5.6-terra", "high"))

    def test_material_judgment_uses_sol_high(self):
        result = ROUTER.recommend(args(judgment=2))
        self.assertEqual((result["model"], result["reasoning_effort"]),
                         ("gpt-5.6-sol", "high"))

    def test_children_are_capped(self):
        result = ROUTER.recommend(args(parallel_parts=5, max_children=2))
        self.assertEqual(result["subagents"], 2)
        self.assertEqual(result["fork_turns"], "none")

    def test_repeatable_workers_start_on_luna(self):
        result = ROUTER.recommend(args(clarity=2, repeatable=True, parallel_parts=2))
        self.assertEqual(result["child_starting_route"], "gpt-5.6-luna/high")

    def test_shared_writes_suppress_parallelism(self):
        result = ROUTER.recommend(args(parallel_parts=3, shared_writes=True))
        self.assertEqual(result["subagents"], 0)
        self.assertTrue(result["warnings"])


if __name__ == "__main__":
    unittest.main()
