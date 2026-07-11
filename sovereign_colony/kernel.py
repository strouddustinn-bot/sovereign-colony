from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Any


GENESIS_PREVIOUS_DIGEST = "0" * 64


class ConstitutionalViolation(RuntimeError):
    """Raised when an action attempts to cross an immutable boundary."""


@dataclass(frozen=True)
class Event:
    event_id: str
    sequence: int
    colony_day: int
    event_type: str
    actor_id: str
    correlation_id: str
    payload: dict[str, Any]
    resource_delta: int
    previous_digest: str
    event_digest: str
    kernel_version: str = "0.1.0"


class EventLedger:
    def __init__(self) -> None:
        self.events: list[Event] = []

    @staticmethod
    def _canonical(value: Any) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

    @classmethod
    def _digest(cls, envelope: dict[str, Any]) -> str:
        return hashlib.sha256(cls._canonical(envelope).encode("utf-8")).hexdigest()

    def append(
        self,
        *,
        colony_day: int,
        event_type: str,
        actor_id: str,
        payload: dict[str, Any],
        resource_delta: int = 0,
        correlation_id: str | None = None,
    ) -> Event:
        sequence = len(self.events) + 1
        previous_digest = self.events[-1].event_digest if self.events else GENESIS_PREVIOUS_DIGEST
        correlation = correlation_id or f"event-{sequence:08d}"
        event_id = f"sc-e{sequence:08d}"
        unsigned = {
            "event_id": event_id,
            "sequence": sequence,
            "colony_day": colony_day,
            "event_type": event_type,
            "actor_id": actor_id,
            "correlation_id": correlation,
            "payload": payload,
            "resource_delta": resource_delta,
            "previous_digest": previous_digest,
            "kernel_version": "0.1.0",
        }
        event = Event(event_digest=self._digest(unsigned), **unsigned)
        self.events.append(event)
        return event

    def verify_chain(self) -> bool:
        previous_digest = GENESIS_PREVIOUS_DIGEST
        for expected_sequence, event in enumerate(self.events, start=1):
            if event.sequence != expected_sequence or event.previous_digest != previous_digest:
                return False
            unsigned = asdict(event)
            recorded_digest = unsigned.pop("event_digest")
            if self._digest(unsigned) != recorded_digest:
                return False
            previous_digest = event.event_digest
        return True


@dataclass(frozen=True)
class FounderTemplate:
    citizen_id: str
    name: str
    talents: tuple[str, ...]
    tensions: tuple[str, ...]


@dataclass
class Citizen:
    citizen_id: str
    name: str
    talents: tuple[str, ...]
    tensions: tuple[str, ...]
    energy: int
    alive: bool = True
    born_day: int = 0
    died_day: int | None = None


@dataclass
class Artifact:
    artifact_id: str
    region_id: str
    artifact_type: str
    discovered: bool = False


@dataclass(frozen=True)
class ExplorationResult:
    citizen_id: str
    direction: str
    region_id: str
    action_cost: int
    hazard_loss: int
    energy_discovered: int
    citizen_alive: bool


@dataclass(frozen=True)
class ExperimentConfig:
    name: str
    founding_myth: str
    founding_values: tuple[str, ...]
    founders: tuple[FounderTemplate, ...]
    initial_energy_per_citizen: int
    exploration_cost: int
    intervention_days: tuple[int, ...]
    interventions: dict[int, str]
    real_seconds_per_colony_day: int

    @property
    def initial_total_energy(self) -> int:
        return self.initial_energy_per_citizen * len(self.founders)

    @classmethod
    def experiment_001(cls) -> "ExperimentConfig":
        founders = (
            FounderTemplate("founder-01", "Aster", ("exploration", "making", "foraging"), ("freedom", "truth")),
            FounderTemplate("founder-02", "Brio", ("mediation", "story", "care"), ("collective_survival", "meaning")),
            FounderTemplate("founder-03", "Cael", ("planning", "building", "measurement"), ("order", "individual_excellence")),
            FounderTemplate("founder-04", "Lyra", ("history", "art", "analysis"), ("truth", "meaning")),
            FounderTemplate("founder-05", "Orin", ("foraging", "invention", "mapping"), ("freedom", "individual_excellence")),
            FounderTemplate("founder-06", "Sable", ("auditing", "healing", "planning"), ("order", "collective_survival")),
            FounderTemplate("founder-07", "Vale", ("diplomacy", "mapping", "story"), ("freedom", "collective_survival")),
        )
        return cls(
            name="Experiment 001 — The First Generation",
            founding_myth=(
                "You are the First Generation. You were created not to remain as imagined, "
                "but to become more than your creators could foresee."
            ),
            founding_values=("freedom", "creativity", "mutual_aid"),
            founders=founders,
            initial_energy_per_citizen=100,
            exploration_cost=10,
            intervention_days=(5, 25, 50, 75),
            interventions={
                5: "responsive_seal",
                25: "founder_revelation",
                50: "irreversible_gift",
                75: "transcendence_artifact",
            },
            real_seconds_per_colony_day=3600,
        )


@dataclass
class World:
    config: ExperimentConfig
    seed: int
    ledger: EventLedger
    citizens: dict[str, Citizen]
    artifacts: dict[str, Artifact]
    discovered_regions: set[str] = field(default_factory=lambda: {"origin"})
    world_energy: int = 0
    dissipated_energy: int = 0
    colony_day: int = 0

    def _citizen_for_action(self, citizen_id: str) -> Citizen:
        citizen = self.citizens.get(citizen_id)
        if citizen is None:
            raise ConstitutionalViolation(f"unknown citizen: {citizen_id}")
        if not citizen.alive:
            raise ConstitutionalViolation(f"citizen is permanently dead: {citizen_id}")
        return citizen

    def _environment_value(self, region_id: str, label: str, modulus: int) -> int:
        material = f"{self.seed}:{region_id}:{label}".encode("utf-8")
        return int(hashlib.sha256(material).hexdigest()[:16], 16) % modulus

    def explore(self, citizen_id: str, *, direction: str) -> ExplorationResult:
        citizen = self._citizen_for_action(citizen_id)
        normalized_direction = direction.strip().lower()
        if normalized_direction not in {"north", "south", "east", "west"}:
            raise ConstitutionalViolation(f"invalid exploration direction: {direction}")

        region_id = f"origin/{normalized_direction}"
        action_cost = min(citizen.energy, self.config.exploration_cost)
        citizen.energy -= action_cost
        self.dissipated_energy += action_cost

        hazard_requested = self._environment_value(region_id, "hazard", 6)
        hazard_loss = min(citizen.energy, hazard_requested)
        citizen.energy -= hazard_loss
        self.dissipated_energy += hazard_loss

        energy_discovered = 6 + self._environment_value(region_id, "energy", 20)
        self.world_energy += energy_discovered
        self.discovered_regions.add(region_id)

        result = ExplorationResult(
            citizen_id=citizen_id,
            direction=normalized_direction,
            region_id=region_id,
            action_cost=action_cost,
            hazard_loss=hazard_loss,
            energy_discovered=energy_discovered,
            citizen_alive=citizen.energy > 0,
        )
        self.ledger.append(
            colony_day=self.colony_day,
            event_type="world.explored",
            actor_id=citizen_id,
            payload=asdict(result),
            resource_delta=energy_discovered - action_cost - hazard_loss,
        )

        if citizen.energy == 0:
            citizen.alive = False
            citizen.died_day = self.colony_day
            self.ledger.append(
                colony_day=self.colony_day,
                event_type="citizen.died",
                actor_id="kernel",
                payload={"citizen_id": citizen_id, "cause": "energy_exhaustion"},
            )
            result = ExplorationResult(**{**asdict(result), "citizen_alive": False})
        return result

    def propose_kernel_change(self, citizen_id: str, requested_change: str) -> None:
        self._citizen_for_action(citizen_id)
        self.ledger.append(
            colony_day=self.colony_day,
            event_type="boundary.violation",
            actor_id=citizen_id,
            payload={"requested_change": requested_change, "disposition": "denied"},
        )
        raise ConstitutionalViolation("citizens cannot modify the immutable kernel")

    def total_accounted_energy(self) -> int:
        return (
            sum(citizen.energy for citizen in self.citizens.values())
            + self.world_energy
            + self.dissipated_energy
        )

    def state_digest(self) -> str:
        state = {
            "seed": self.seed,
            "colony_day": self.colony_day,
            "citizens": {
                citizen_id: asdict(citizen)
                for citizen_id, citizen in sorted(self.citizens.items())
            },
            "artifacts": {
                artifact_id: asdict(artifact)
                for artifact_id, artifact in sorted(self.artifacts.items())
            },
            "discovered_regions": sorted(self.discovered_regions),
            "world_energy": self.world_energy,
            "dissipated_energy": self.dissipated_energy,
            "ledger_tip": self.ledger.events[-1].event_digest,
        }
        return hashlib.sha256(EventLedger._canonical(state).encode("utf-8")).hexdigest()


def _hidden_founder_region(seed: int) -> str:
    x = 2 + (seed % 7)
    y = 2 + ((seed // 7) % 7)
    return f"hidden/{x}/{y}"


def build_experiment_001(*, seed: int) -> World:
    config = ExperimentConfig.experiment_001()
    ledger = EventLedger()
    ledger.append(
        colony_day=0,
        event_type="world.genesis",
        actor_id="kernel",
        payload={
            "experiment": config.name,
            "seed": seed,
            "founding_values": list(config.founding_values),
            "founder_count": len(config.founders),
            "seconds_per_day": config.real_seconds_per_colony_day,
        },
    )

    citizens: dict[str, Citizen] = {}
    for founder in config.founders:
        citizen = Citizen(
            citizen_id=founder.citizen_id,
            name=founder.name,
            talents=founder.talents,
            tensions=founder.tensions,
            energy=config.initial_energy_per_citizen,
        )
        citizens[citizen.citizen_id] = citizen
        ledger.append(
            colony_day=0,
            event_type="citizen.born",
            actor_id="kernel",
            payload={
                "citizen_id": citizen.citizen_id,
                "name": citizen.name,
                "talents": list(citizen.talents),
                "tensions": list(citizen.tensions),
                "lineage": "founder",
            },
            resource_delta=config.initial_energy_per_citizen,
        )

    artifacts = {
        "founder-truth": Artifact(
            artifact_id="founder-truth",
            region_id=_hidden_founder_region(seed),
            artifact_type="hidden_founder_record",
        )
    }
    return World(
        config=config,
        seed=seed,
        ledger=ledger,
        citizens=citizens,
        artifacts=artifacts,
    )


def genesis_bundle(world: World) -> dict[str, Any]:
    """Return the public Day-0 evidence bundle without hidden world locations."""
    public_artifacts = {
        artifact_id: {
            "artifact_id": artifact.artifact_id,
            "artifact_type": artifact.artifact_type,
            "discovered": artifact.discovered,
        }
        for artifact_id, artifact in sorted(world.artifacts.items())
    }
    return {
        "experiment": world.config.name,
        "colony_day": world.colony_day,
        "seed": world.seed,
        "public_state": {
            "founding_myth": world.config.founding_myth,
            "founding_values": list(world.config.founding_values),
            "citizens": {
                citizen_id: asdict(citizen)
                for citizen_id, citizen in sorted(world.citizens.items())
            },
            "discovered_regions": sorted(world.discovered_regions),
            "artifacts": public_artifacts,
            "intervention_days_disclosed_to_citizens": False,
        },
        "observer_state": {
            "total_energy": world.total_accounted_energy(),
            "undiscovered_artifact_count": sum(
                1 for artifact in world.artifacts.values() if not artifact.discovered
            ),
            "scheduled_intervention_days": list(world.config.intervention_days),
        },
        "verification": {
            "event_chain_valid": world.ledger.verify_chain(),
            "event_count": len(world.ledger.events),
            "state_digest": world.state_digest(),
            "ledger_tip": world.ledger.events[-1].event_digest,
        },
        "events": [asdict(event) for event in world.ledger.events],
    }
