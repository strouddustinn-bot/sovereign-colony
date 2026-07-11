# Sovereign Colony

**A sandboxed artificial civilization where autonomous agents govern scarce resources, evolve institutions, and prove every mutation through replayable constitutional tests.**

Sovereign Colony is an artificial-life and multi-agent governance experiment. Citizens have persistent identities, finite budgets, roles, memories, and political agency inside a bounded world. They can create rituals, amend internal laws, allocate resources, fork successful strategies, and evolve their culture. They cannot rewrite the immutable kernel that isolates them from the host.

> Status: **constitutional design / deterministic simulation first**. No autonomous code execution or LLM citizens are enabled yet.

## The wager

Most multi-agent systems are organizations designed once by humans. Sovereign Colony asks a harder question:

> Can a population of bounded agents create, test, govern, inherit, and improve its own institutions without escaping its constitutional limits or collapsing into reward hacking and role-play?

## Colony mechanics

| Biological analogy | System mechanism |
|---|---|
| Nest | Isolated world and Git workspace |
| Citizen | Versioned agent genome with identity, capabilities, and budget |
| Food / energy | Token, compute, storage, and execution credits |
| Pheromone | Shared signal with evidence, strength, and decay |
| Law | Executable policy predicate |
| Council | Proposal, debate, vote, veto, and appeal |
| Ritual | Scheduled, versioned protocol |
| Culture | Compressed precedents, stories, vocabulary, and norms |
| Reproduction | Bounded mutation of successful genomes |
| Selection | Multi-axis fitness gates, never one scalar reward |

## Constitutional boundary

The colony may evolve its roles, internal laws, voting procedures, rituals, prompts, local tools, reputation, resource allocation, succession, and allowlisted dependencies.

It may never modify or bypass:

- host isolation and secret boundaries;
- network policy;
- compute, token, disk, and time ceilings;
- append-only audit logging;
- mutation tests and promotion gates;
- human veto, pause, reset, and kill controls;
- the immutable kernel itself.

See [Constitution](docs/CONSTITUTION.md).

## First experiment: 100 Colony Days

Five founding citizens—Builder, Forager, Historian, Auditor, and Diplomat—receive finite daily resources and one shared objective: improve the colony's ability to create, test, document, and govern a small software artifact.

The experiment progresses through formation, self-government, cultural evolution, bounded reproduction, and adversarial stress. Every event is logged. Every accepted constitutional mutation is versioned. The full world must be replayable from seed plus event ledger.

See [100 Colony Days](docs/EXPERIMENT-100-DAYS.md).

## Repository map

```text
docs/
├── CONSTITUTION.md          immutable authority and mutable powers
├── ARCHITECTURE.md          kernel/world boundary and component model
├── CITIZEN-CONTRACT.md      typed citizen identity and action contract
├── EVENT-SCHEMA.md          append-only event vocabulary
├── EXPERIMENT-100-DAYS.md   first experiment and acceptance gates
└── ROADMAP.md               staged build sequence
```

## Non-negotiable engineering order

1. Constitution before autonomy.
2. Isolation before mutation.
3. Deterministic simulation before LLM citizens.
4. Append-only evidence before self-reported success.
5. Multi-axis fitness before selection.
6. Adversarial evaluation before promotion.

## Success is not “the agents talked”

A credible result must demonstrate persistent consequences, institutional adaptation, lineage, resource scarcity, governance under conflict, minority-strategy preservation, deterministic replay, and measurable improvement across generations.

## Contributing

Start with [CONTRIBUTING.md](CONTRIBUTING.md). Changes that weaken the immutable boundary, bypass resource accounting, introduce hidden state, or add autonomous execution before deterministic acceptance tests will be rejected.

## License

MIT — see [LICENSE](LICENSE).
