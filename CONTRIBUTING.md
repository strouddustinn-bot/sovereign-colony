# Contributing

Sovereign Colony rewards disciplined experiments, not autonomy theater.

## Before proposing code

1. Read `docs/CONSTITUTION.md`.
2. Identify whether the change belongs to the immutable kernel or evolvable world.
3. State the invariant or research question.
4. Write a failing behavioral test first.
5. Keep the implementation deterministic until Phase 4.

## Pull-request requirements

- One focused change.
- Threat and failure analysis.
- Tests that failed before implementation and pass afterward.
- Replay impact documented.
- Resource-accounting impact documented.
- No secrets, host paths, or ambient environment dependencies.
- No weakening of immutable articles.

## Rejected patterns

- Free-form shell access for citizens.
- Hidden mutable state.
- Single-number fitness.
- Network-on by default.
- “The agent said it succeeded” as verification.
- Autonomous code execution before deterministic world acceptance tests.
- Changes that cannot be replayed or rolled back.
