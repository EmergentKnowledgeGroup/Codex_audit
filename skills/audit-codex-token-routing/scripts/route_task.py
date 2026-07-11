#!/usr/bin/env python3
"""Print a provisional Codex route recommendation; never changes configuration."""

from __future__ import annotations

import argparse
import json


def recommend(args: argparse.Namespace) -> dict[str, object]:
    reasons: list[str] = []
    warnings: list[str] = []
    work_type = getattr(args, "work_type", "implementation")
    role = getattr(args, "role", "worker")
    spec_gated = bool(getattr(args, "spec_gated", False))

    if args.judgment == 2:
        model, effort = "gpt-5.6-sol", "high"
        reasons.append("material architecture, security, release, or conflicting-evidence judgment")
    elif role == "controller" and spec_gated and args.clarity == 2 and args.validation >= 1:
        model, effort = "gpt-5.6-luna", "xhigh"
        reasons.append("clear spec-gated control-plane work with measurable acceptance")
    elif work_type == "qa":
        model, effort = "gpt-5.6-sol", "low"
        reasons.append("judgment-oriented QA/review pass")
    elif work_type == "integration_qa":
        model, effort = "gpt-5.6-terra", "high"
        reasons.append("scope reconciliation or meaningful integration QA")
    elif work_type in {"inventory", "extraction"} and args.clarity == 2 and args.blast == 0:
        model, effort = "gpt-5.6-luna", "low"
        reasons.append("clear mechanical lookup, extraction, or inventory")
    elif args.clarity == 2 and args.blast == 0 and work_type in {"implementation", "tracing"}:
        model = "gpt-5.6-luna"
        effort = "high"
        reasons.append("clear ordinary implementation or tracing")
    else:
        model = "gpt-5.6-terra"
        effort = "high" if args.blast == 2 or args.judgment == 1 else "medium"
        reasons.append("ordinary multi-step work with depth or tradeoffs")

    if args.validation == 0:
        warnings.append("Define acceptance evidence before increasing effort or fan-out.")

    independent = args.parallel_parts >= 2 and not args.shared_writes
    child_count = min(args.parallel_parts, args.max_children) if independent else 0
    child_route = None
    if child_count:
        if work_type in {"inventory", "extraction"} and args.clarity == 2:
            child_route = "gpt-5.6-luna/low"
        elif work_type == "integration_qa":
            child_route = "gpt-5.6-terra/high"
        elif work_type == "qa":
            child_route = "gpt-5.6-sol/low"
        else:
            child_route = ("gpt-5.6-luna/high" if args.repeatable and args.clarity == 2
                           and args.validation >= 1 else "gpt-5.6-terra/high")
    if args.parallel_parts >= 2 and args.shared_writes:
        warnings.append("Parallel workers suppressed because writes overlap.")

    return {
        "schema_version": 1,
        "recommendation_only": True,
        "model": model,
        "reasoning_effort": effort,
        "subagents": child_count,
        "child_starting_route": child_route,
        "fork_turns": "none" if child_count else None,
        "reasons": reasons,
        "warnings": warnings,
        "next_step": "Validate this route on a paired task before changing global defaults.",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clarity", type=int, choices=range(3), required=True,
                        help="0 ambiguous, 1 mixed, 2 crisp acceptance criteria")
    parser.add_argument("--blast", type=int, choices=range(3), required=True,
                        help="0 isolated, 1 subsystem, 2 repo/release-wide")
    parser.add_argument("--judgment", type=int, choices=range(3), required=True,
                        help="0 mechanical, 1 tradeoffs, 2 architecture/security/release")
    parser.add_argument("--validation", type=int, choices=range(3), default=2,
                        help="0 subjective, 1 partial, 2 strong evidence")
    parser.add_argument("--parallel-parts", type=int, default=0,
                        help="independent candidate work packages")
    parser.add_argument("--max-children", type=int, default=2,
                        help="recommendation cap; default 2")
    parser.add_argument("--repeatable", action="store_true")
    parser.add_argument("--work-type", choices=("inventory", "extraction", "implementation", "tracing", "qa", "integration_qa"),
                        default="implementation",
                        help="work shape; default implementation")
    parser.add_argument("--role", choices=("controller", "worker"), default="worker",
                        help="route role; controller requires --spec-gated")
    parser.add_argument("--spec-gated", action="store_true",
                        help="contract/checklist/blockerboard/acceptance criteria are explicit")
    parser.add_argument("--shared-writes", action="store_true")
    args = parser.parse_args()
    if args.parallel_parts < 0:
        parser.error("--parallel-parts must be >= 0")
    if not 0 <= args.max_children <= 8:
        parser.error("--max-children must be between 0 and 8")
    return args


def main() -> None:
    print(json.dumps(recommend(parse_args()), indent=2))


if __name__ == "__main__":
    main()
