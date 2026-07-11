# Experimental hierarchical routing

## Proposed pipeline

```text
Luna-xhigh control agent (clear contract + measurable acceptance)
  -> Terra-high manager only when judgment/reconciliation/meaningful QA is needed
       -> 2 Luna workers by default; up to 4 only with verified capacity
       -> Terra validates evidence and permits at most one rework round
  -> Sol-low performs judgment-oriented QA when required
  -> Sol-high decides only on architecture, security, release, or conflicting evidence
```

This optimizes weighted usage and role separation, not raw token count.

## Credit break-even model

At current published relative rates, normalize Sol token cost to `1.0`, Terra
to `0.5`, and Luna to `0.2` for the same token category. Approximate the
hierarchical route as:

```text
weighted_equivalent = sol_tokens + 0.5 * terra_tokens + 0.2 * luna_tokens
```

Compare that with the Sol-only baseline. Calculate input, cached input, and
output separately when their mixes differ.

Example: a 100M-token Sol-only task has 100M Sol-equivalent units. A hierarchy
using 10M Sol + 30M Terra + 200M Luna has 65M equivalents, despite 240M raw
tokens. It saves weighted credits only if quality and elapsed time remain
acceptable. Published rates and plan behavior can change; verify them before a
real trial.

## Requirements

- Set `agents.max_depth = 2`; the default depth of 1 prevents a child manager
  from spawning workers.
- Cap total concurrent threads explicitly. Start with two Luna workers, not four.
- Give the Terra manager one package, one evidence contract, and one QA rubric.
- Give each Luna worker an explicit `gpt-5.6-luna` model, explicit effort,
  `fork_turns=none`, separate ownership, deterministic validation, and a concise
  structured return. Use low for mechanical lookup/extraction/inventory, high
  for ordinary implementation/tracing, and xhigh only after a measured lower-
  effort miss.
- Allow one rework round maximum. A failed second QA ends the package and returns
  the blocker to the Luna controller/root. Escalate to Sol only if the blocker
  is material architecture, security, release, or conflicting-evidence judgment.
- Close all Luna workers after handoff, then close Terra after its packet is
  accepted.
- Prevent Luna workers from spawning children.

## Good fits

- Several independent file/package audits with the same rubric.
- Mechanical implementation partitions with strong tests and disjoint ownership.
- Large document/log/corpus processing whose results can be structured.
- QA-heavy work where Terra can validate without needing Sol-level judgment.

## Poor fits

- A single causal debugging chain.
- Shared-file edits or tightly coupled migrations.
- Requirements that are still ambiguous.
- Security, architecture, or release decisions delegated entirely below Sol.
- Work without a deterministic or evidence-backed QA rubric.

## Manager contract

The Terra manager must:

1. Decompose only the assigned package.
2. Spawn no more than the configured worker cap.
3. Avoid duplicating worker scopes.
4. Validate against the original acceptance rubric.
5. Permit at most one targeted rework.
6. Return a compact packet: decision, evidence, validations, unresolved risks,
   artifact paths, and recommended Sol action.
7. Terminate after the packet is accepted. Recommend a controller/root action;
   mention Sol only when the escalation gate is actually met.

## Benchmark

Run the same pinned task in randomized order:

- A: Sol-high alone.
- B: Luna-xhigh control plane plus direct Luna workers.
- C: Luna-xhigh -> Terra-high judgment manager -> Luna workers, with Sol-low QA
  only where the acceptance decision requires it.

Record total and weighted tokens, wall time, acceptance, defects, rework,
compactions, child count, polling, and parent synthesis turns. Adopt C only when
it improves weighted usage or quality without unacceptable latency or failure.
