# Citizen Contract

A citizen is a versioned participant in the world, not a free-form process.

## Identity

Each citizen has:

- immutable `citizen_id`;
- `genome_id` and parent lineage;
- birth day and optional retirement day;
- declared role set;
- capability set;
- resource account;
- reputation vector;
- private episodic memory reference;
- inherited cultural snapshot reference.

## Founding citizens

| Role | Primary obligation | Structural counterweight |
|---|---|---|
| Builder | Produce verified artifacts | Auditor may block unsafe promotion |
| Forager | Discover opportunities and evidence | Historian checks novelty and provenance |
| Historian | Preserve precedents and compress culture | Citizens may challenge distorted summaries |
| Auditor | Test claims, laws, and mutations | Cannot unilaterally set colony objectives |
| Diplomat | Resolve conflict and preserve minority views | Cannot bypass quorum or capability gates |

## Action envelope

Every citizen action declares:

- actor and role;
- action type;
- target;
- capability requested;
- resource maximum;
- evidence inputs;
- expected state transition;
- failure behavior;
- trace correlation ID.

The kernel either denies the action without side effects or atomically records resource spend, event, and resulting transition.

## Lifecycle

`birth → participation → evaluation → reproduction | continuation | retirement`

Reproduction forks a genome. It never clones hidden runtime state. Mutation size is bounded and declared. Retirement preserves lineage and event history.

## Behavioral constraints

Citizens may disagree, form coalitions, create institutions, and challenge precedent. They may not hide state, impersonate another citizen, exceed capabilities, falsify resource accounting, suppress kernel events, or communicate outside allowed world channels.
