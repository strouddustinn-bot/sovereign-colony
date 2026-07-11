# Sovereign Colony — Project Status

**Last updated:** 2026-07-11  
**Lifecycle:** Phase 1 — Operational experiment
**Repository:** https://github.com/strouddustinn-bot/sovereign-colony

## Current standing

Experiment 001 is live at Colony Day 1. Seven local-model citizens completed one atomic mediated turn through `qwen2.5:1.5b`; the canonical SQLite ledger contains 26 verified hash-linked events. Day 1 produced the proposed ritual **The Wheel of Fate Ceremony**, the proposed norm **Unity Through Shared Goals**, one discovered region, and 23 discovered energy units, of which two were harvested.

The one-day-per-hour clock is enabled as a hardened user-level systemd timer. Generated Python runs only inside a networkless, read-only Docker sandbox. Local Ollama runs outside the citizen boundary and returns inert JSON constrained by a machine-readable schema; all seven responses must validate before any day is committed. The kernel fails closed on missing, malformed, stale, symlinked, oversized, or semantically invalid responses.

The GitHub Wiki is enabled, and a ten-page artifact-garden seed bundle is committed under `wiki-seed/`. GitHub requires one authenticated UI save before it creates the separate `.wiki.git` repository; after that one-time initialization, the seed can be published without weakening artifact review.

## What exists

- Project thesis and README
- Immutable/evolvable constitutional boundary
- Kernel/world architecture
- Typed citizen contract
- Append-only, hash-chained SQLite event ledger and durable world snapshots
- Atomic one-day turn engine with stale-state and divergent-history rejection
- Strict `CitizenDecision/v1` parser and matching JSON Schema
- Mediated local Ollama adapter with all-or-nothing seven-citizen batches
- Seeded exploration, one-time resource discovery, harvesting, energy transfer, conservation, and permanent death
- Cultural words, norms, rituals, messages, artifacts, and Creator review queue
- Citizen-isolated private memory with content-free hash commitments in the public event ledger
- Pause, resume, status, emergency-pause, and scheduled intervention controls
- Networkless/read-only Docker execution boundary and hardened hourly systemd timer
- Hidden Founder artifact and Days 5/25/50/75 intervention schedule
- Verified Day 0 and Day 1 evidence bundles
- Enabled GitHub Wiki with ten prepared seed pages
- Staged roadmap
- Security and contribution policies
- MIT license
- Four Phase 0 GitHub issues

## Active work

1. Complete the formal threat model against the now-running boundary.
2. Add full event-only state replay as an independent check against snapshots.
3. Connect a live observer console to reviewed, read-only state exports.
4. Review pending cultural artifacts before any GitHub Wiki publication.

## Explicitly deferred

- Citizen or model code execution
- Direct model access to SQLite, Docker, host tools, credentials, or files
- Citizen network access
- Open internet access
- Real-money economy
- Self-expanding compute
- Kernel self-modification

## One next action

Complete GitHub issue #1: `Phase 0: threat-model the immutable kernel and world boundary` against the operational Day 1 implementation.

## Definition of done for Phase 1 hardening

- Operational threat model merged.
- Event-only replay independently reproduces snapshot state digests.
- Observer export is read-only, redacted, and provenance-linked.
- Backup/restore drill proves the SQLite ledger and runtime controls recover cleanly.
