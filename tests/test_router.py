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
        "work_type": "implementation",
        "role": "worker",
        "spec_gated": False,
        "shared_writes": False,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class RouterTests(unittest.TestCase):
    def test_clear_ordinary_implementation_uses_luna_high(self):
        result = ROUTER.recommend(args(clarity=2, blast=0, repeatable=True))
        self.assertEqual((result["model"], result["reasoning_effort"]),
                         ("gpt-5.6-luna", "high"))

    def test_inventory_uses_luna_low(self):
        result = ROUTER.recommend(args(work_type="inventory", clarity=2, blast=0, judgment=0))
        self.assertEqual((result["model"], result["reasoning_effort"]),
                         ("gpt-5.6-luna", "low"))

    def test_spec_gated_controller_uses_luna_xhigh(self):
        result = ROUTER.recommend(args(role="controller", spec_gated=True, clarity=2, blast=2, judgment=0))
        self.assertEqual((result["model"], result["reasoning_effort"]),
                         ("gpt-5.6-luna", "xhigh"))

    def test_integration_qa_uses_terra_high(self):
        result = ROUTER.recommend(args(work_type="integration_qa", clarity=2, blast=1, judgment=0))
        self.assertEqual((result["model"], result["reasoning_effort"]),
                         ("gpt-5.6-terra", "high"))

    def test_non_material_ambiguity_does_not_escalate_to_sol(self):
        result = ROUTER.recommend(args(clarity=0, blast=1, judgment=0))
        self.assertEqual(result["model"], "gpt-5.6-terra")

    def test_judgment_qa_uses_sol_low(self):
        result = ROUTER.recommend(args(work_type="qa", clarity=2, blast=0, judgment=0))
        self.assertEqual((result["model"], result["reasoning_effort"]),
                         ("gpt-5.6-sol", "low"))

    def test_cross_module_tradeoff_uses_terra_high(self):
        result = ROUTER.recommend(args(blast=2, judgment=1))
        self.assertEqual((result["model"], result["reasoning_effort"]),
                         ("gpt-5.6-terra", "high"))

    def test_material_judgment_uses_sol_high(self):
        result = ROUTER.recommend(args(judgment=2))
        self.assertEqual((result["model"], result["reasoning_effort"]),
                         ("gpt-5.6-sol", "high"))

    def test_children_are_capped(self):
        result = ROUTER.recommend(args(parallel_parts=8, max_children=8))
        self.assertEqual(result["subagents"], 4)
        self.assertEqual(result["fork_turns"], "none")

    def test_children_default_cap_remains_two(self):
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
