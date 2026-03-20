# Mission Continuity Final Increment

## Objective

Execute one last cognitive increment for the `v1` so the system behaves more like a single ongoing intelligence across turns and missions, not only a well-structured request pipeline.

## Scope

This increment strengthens continuity between missions in the current nucleus. It does not add new services, external dependencies, or multimodal features.

## Implementation Focus

1. Recover mission signals with stronger precedence.
2. Make planning explicitly react to:
   - active mission goal
   - open loops
   - last decision frame
   - conflict between the current request and the active mission
3. Make synthesis sound like a continuation or reformulation of the same entity.
4. Preserve governance and operational safety already established in the `v1`.

## Work Items

1. Enrich `PlanningContext` with mission goal and prior recommendation recovered from memory.
2. Improve mission recovery ordering in `memory-service` so continuity hints arrive in a stable priority.
3. Harden `planning-engine` to choose between `continuar`, `encerrar`, and `reformular` with explicit mission-goal conflict handling.
4. Improve `synthesis-engine` so the final response reflects continuity, closure, or reformulation without exposing pipeline internals.
5. Add regression tests for:
   - mission continuation
   - mission closure
   - mission-goal conflict and reformulation

## Acceptance Criteria

- A second turn in the same mission clearly continues or closes the active loop.
- A new request that conflicts with an active mission is treated as reformulation, not as silent scope drift.
- The final response sounds unitary and mission-aware.
- `pytest -q` and `ruff check` remain green on the touched files.