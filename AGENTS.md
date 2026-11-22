# Sovereign Colony — repository instructions

## Purpose and state
Sandboxed artificial civilization and constitutional agent-governance experiment. The README describes a **deterministic simulation-first** implementation; LLM citizens and autonomous code execution are not enabled. Do not describe a simulation as a deployed autonomous society.

## Design invariants
- Keep immutable host-isolation rules outside citizen-editable governance.
- Model finite budgets, permissions, decision records, and resource allocations deterministically.
- Test institutional changes through replayable scenarios; state any randomness and seeds.
- No host command execution, live financial transactions, irreversible file mutations, or unsupervised external messaging from simulated citizens.
- Preserve auditability and distinguish simulated evidence from real-world results.

## Development and verification
Read `README.md`, inspect source and test configuration before changing the simulation, and use only verified local commands. Prefer repeatable unit and scenario tests for constitutional limits. Document unimplemented features, side effects, and any changed invariants.
