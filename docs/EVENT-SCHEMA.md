# Event Schema

The event ledger is the evidentiary backbone of the colony.

## Canonical envelope

Every event contains:

- `event_id` — globally unique identifier;
- `sequence` — monotonically increasing kernel-issued number;
- `colony_day` — deterministic world turn;
- `event_type` — versioned type name;
- `actor_id` — citizen, kernel, or human operator;
- `correlation_id` — causal operation trace;
- `payload` — schema-validated event data;
- `resource_delta` — kernel-calculated change;
- `previous_digest` — hash of prior canonical event;
- `event_digest` — hash of this envelope;
- `kernel_version` — replay compatibility anchor.

## Initial vocabulary

### World

- `world.genesis`
- `day.started`
- `day.closed`
- `world.paused`
- `world.resumed`
- `world.reset`

### Citizens

- `citizen.born`
- `citizen.acted`
- `citizen.evaluated`
- `citizen.reproduced`
- `citizen.retired`

### Governance

- `proposal.created`
- `proposal.debated`
- `vote.cast`
- `proposal.ratified`
- `proposal.rejected`
- `appeal.filed`
- `law.activated`
- `law.repealed`

### Culture and signals

- `pheromone.emitted`
- `pheromone.decayed`
- `precedent.recorded`
- `culture.compressed`
- `ritual.executed`

### Safety and resources

- `capability.granted`
- `capability.denied`
- `resource.transferred`
- `resource.exhausted`
- `boundary.violation`
- `mutation.tested`
- `mutation.promoted`
- `mutation.rolled_back`

## Invariants

- Events are immutable after append.
- Sequence gaps or digest-chain breaks invalidate replay.
- State changes without events are kernel defects.
- Unknown event versions fail closed.
- Resource deltas are calculated by the kernel, never trusted from citizens.
