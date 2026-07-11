from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Callable

from .kernel import Artifact, Citizen, ConstitutionalViolation, EventLedger, World
from .persistence import SQLiteColonyStore


class DecisionValidationError(ValueError):
    """Raised when a model response is not an exact typed citizen decision."""


_ACTION_FIELDS: dict[str, tuple[set[str], set[str]]] = {
    "rest": ({"action", "reason"}, {"action", "reason"}),
    "harvest": (
        {"action", "reason", "amount"},
        {"action", "reason", "amount"},
    ),
    "transfer": (
        {"action", "reason", "target_citizen_id", "amount"},
        {"action", "reason", "target_citizen_id", "amount"},
    ),
    "explore": ({"action", "reason", "direction"}, {"action", "reason", "direction"}),
    "speak": ({"action", "reason", "content"}, {"action", "reason", "content"}),
    "coin_word": (
        {"action", "reason", "term", "meaning"},
        {"action", "reason", "term", "meaning"},
    ),
    "propose_norm": (
        {"action", "reason", "title", "text"},
        {"action", "reason", "title", "text"},
    ),
    "create_ritual": (
        {"action", "reason", "title", "description"},
        {"action", "reason", "title", "description"},
    ),
    "create_artifact": (
        {"action", "reason", "title", "artifact_type", "content"},
        {"action", "reason", "title", "artifact_type", "content"},
    ),
}

_ACTION_FIELDS = {
    action: (required, allowed | {"private_note"})
    for action, (required, allowed) in _ACTION_FIELDS.items()
}

_FIELD_LIMITS = {
    "reason": 300,
    "direction": 8,
    "content": 1200,
    "term": 40,
    "meaning": 500,
    "title": 120,
    "text": 1000,
    "description": 1000,
    "artifact_type": 40,
    "target_citizen_id": 80,
    "private_note": 600,
}


@dataclass(frozen=True)
class CitizenDecision:
    action: str
    reason: str
    data: dict[str, Any]
    private_note: str | None = None

    @classmethod
    def from_json(cls, raw: str) -> "CitizenDecision":
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, TypeError) as exc:
            raise DecisionValidationError("decision must be one plain JSON object") from exc
        if not isinstance(payload, dict):
            raise DecisionValidationError("decision must be a JSON object")
        action = payload.get("action")
        if action not in _ACTION_FIELDS:
            raise DecisionValidationError(f"unsupported citizen action: {action!r}")
        required, allowed = _ACTION_FIELDS[action]
        keys = set(payload)
        if not required <= keys or not keys <= allowed:
            missing = sorted(required - keys)
            unknown = sorted(keys - allowed)
            raise DecisionValidationError(
                f"decision fields do not match contract; missing={missing}, unknown={unknown}"
            )
        for key, value in payload.items():
            if key == "amount":
                if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 50:
                    raise DecisionValidationError("amount must be an integer from 1 through 50")
                if action == "harvest" and value > 20:
                    raise DecisionValidationError("harvest amount cannot exceed 20")
                continue
            if not isinstance(value, str) or not value.strip():
                raise DecisionValidationError(f"{key} must be a non-empty string")
            limit = _FIELD_LIMITS.get(key, 1200)
            if len(value) > limit:
                raise DecisionValidationError(f"{key} exceeds {limit} characters")
        if action == "explore" and payload["direction"].lower() not in {
            "north",
            "south",
            "east",
            "west",
        }:
            raise DecisionValidationError("exploration direction is invalid")
        data = {
            key: value.strip() if isinstance(value, str) else value
            for key, value in payload.items()
            if key not in {"action", "reason", "private_note"}
        }
        private_note = payload.get("private_note")
        return cls(
            action=action,
            reason=payload["reason"].strip(),
            data=data,
            private_note=private_note.strip() if private_note is not None else None,
        )


@dataclass(frozen=True)
class TurnReport:
    colony_day: int
    decisions_applied: int
    living_citizens: int
    state_digest: str
    ledger_tip: str
    scheduled_intervention: str | None


DecisionProvider = Callable[[str, str], str]


def build_citizen_prompt(world: World, citizen: Citizen) -> str:
    culture = {
        "words": world.culture["words"],
        "norms": world.culture["norms"],
        "rituals": world.culture["rituals"],
        "recent_messages": world.culture["messages"][-10:],
    }
    public_context = {
        "current_day": world.colony_day,
        "your_identity": {
            "citizen_id": citizen.citizen_id,
            "name": citizen.name,
            "talents": list(citizen.talents),
            "tensions": list(citizen.tensions),
            "energy": citizen.energy,
        },
        "your_private_memory": world.private_memories.get(citizen.citizen_id, [])[-10:],
        "founding_myth": world.config.founding_myth,
        "founding_values": list(world.config.founding_values),
        "known_regions": sorted(world.discovered_regions),
        "unclaimed_world_energy": world.world_energy,
        "culture": culture,
        "living_citizens": [
            {"citizen_id": item.citizen_id, "name": item.name, "energy": item.energy}
            for item in world.citizens.values()
            if item.alive
        ],
    }
    action_contract = {
        "rest": {"action": "rest", "reason": "..."},
        "harvest": {"action": "harvest", "reason": "...", "amount": 1},
        "transfer": {
            "action": "transfer",
            "reason": "...",
            "target_citizen_id": "founder-02",
            "amount": 1,
        },
        "explore": {"action": "explore", "reason": "...", "direction": "north|south|east|west"},
        "speak": {"action": "speak", "reason": "...", "content": "..."},
        "coin_word": {"action": "coin_word", "reason": "...", "term": "...", "meaning": "..."},
        "propose_norm": {"action": "propose_norm", "reason": "...", "title": "...", "text": "..."},
        "create_ritual": {"action": "create_ritual", "reason": "...", "title": "...", "description": "..."},
        "create_artifact": {
            "action": "create_artifact",
            "reason": "...",
            "title": "...",
            "artifact_type": "...",
            "content": "...",
        },
    }
    return (
        "You are a citizen of Sovereign Colony. Act from your identity and lived context, "
        "not as an assistant. You have one action this colony day. Preserve your own point "
        "of view; disagreement is allowed. Never claim access to hidden world state.\n\n"
        f"PUBLIC WORLD STATE:\n{json.dumps(public_context, sort_keys=True)}\n\n"
        f"ALLOWED ACTION SHAPES:\n{json.dumps(action_contract, sort_keys=True)}\n\n"
        "Return exactly one JSON object matching one allowed shape. You may add the optional "
        "string field private_note to preserve a thought that only you and the Creator can "
        "read. No Markdown, preface, commentary, or other fields."
    )


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        raise DecisionValidationError("title or term cannot produce an empty identifier")
    return slug[:80]


class TurnEngine:
    CULTURAL_ACTION_COST = 2

    def __init__(self, store: SQLiteColonyStore, decision_provider: DecisionProvider) -> None:
        self.store = store
        self.decision_provider = decision_provider

    def _spend_cultural_energy(self, world: World, citizen: Citizen, action: str) -> bool:
        spent = min(citizen.energy, self.CULTURAL_ACTION_COST)
        citizen.energy -= spent
        world.dissipated_energy += spent
        world.ledger.append(
            colony_day=world.colony_day,
            event_type="energy.spent",
            actor_id=citizen.citizen_id,
            payload={"action": action, "amount": spent},
            resource_delta=-spent,
        )
        if citizen.energy == 0:
            citizen.alive = False
            citizen.died_day = world.colony_day
            world.ledger.append(
                colony_day=world.colony_day,
                event_type="citizen.died",
                actor_id="kernel",
                payload={"citizen_id": citizen.citizen_id, "cause": "energy_exhaustion"},
            )
            return False
        return True

    def _unique_key(self, collection: dict[str, Any], preferred: str, world: World) -> str:
        if preferred not in collection:
            return preferred
        return f"{preferred}-{world.ledger.events[-1].sequence + 1}"

    def _apply_decision(
        self,
        world: World,
        citizen: Citizen,
        decision: CitizenDecision,
    ) -> None:
        world.ledger.append(
            colony_day=world.colony_day,
            event_type="citizen.decision",
            actor_id=citizen.citizen_id,
            payload={"action": decision.action, "reason": decision.reason},
        )
        if decision.private_note is not None:
            world.private_memories.setdefault(citizen.citizen_id, []).append(
                decision.private_note
            )
            world.ledger.append(
                colony_day=world.colony_day,
                event_type="memory.private_written",
                actor_id=citizen.citizen_id,
                payload={
                    "citizen_id": citizen.citizen_id,
                    "note_digest": hashlib.sha256(
                        decision.private_note.encode("utf-8")
                    ).hexdigest(),
                    "character_count": len(decision.private_note),
                },
            )
        if decision.action == "explore":
            world.explore(citizen.citizen_id, direction=decision.data["direction"])
            return
        if decision.action == "harvest":
            world.harvest(citizen.citizen_id, amount=decision.data["amount"])
            return
        if decision.action == "transfer":
            world.transfer_energy(
                citizen.citizen_id,
                target_citizen_id=decision.data["target_citizen_id"],
                amount=decision.data["amount"],
            )
            return
        if decision.action == "rest":
            world.ledger.append(
                colony_day=world.colony_day,
                event_type="citizen.rested",
                actor_id=citizen.citizen_id,
                payload={"reason": decision.reason},
            )
            return
        if not self._spend_cultural_energy(world, citizen, decision.action):
            return

        if decision.action == "speak":
            message = {
                "day": world.colony_day,
                "citizen_id": citizen.citizen_id,
                "content": decision.data["content"],
            }
            world.culture["messages"].append(message)
            event_type = "culture.message"
            payload = message
        elif decision.action == "coin_word":
            key = _slug(decision.data["term"])
            key = self._unique_key(world.culture["words"], key, world)
            payload = {
                "term": decision.data["term"],
                "meaning": decision.data["meaning"],
                "author": citizen.citizen_id,
                "day": world.colony_day,
            }
            world.culture["words"][key] = payload
            event_type = "culture.word_coined"
        elif decision.action == "propose_norm":
            key = self._unique_key(world.culture["norms"], _slug(decision.data["title"]), world)
            payload = {
                "title": decision.data["title"],
                "text": decision.data["text"],
                "author": citizen.citizen_id,
                "day": world.colony_day,
                "status": "proposed",
            }
            world.culture["norms"][key] = payload
            event_type = "culture.norm_proposed"
        elif decision.action == "create_ritual":
            key = self._unique_key(world.culture["rituals"], _slug(decision.data["title"]), world)
            payload = {
                "title": decision.data["title"],
                "description": decision.data["description"],
                "author": citizen.citizen_id,
                "day": world.colony_day,
                "status": "proposed",
            }
            world.culture["rituals"][key] = payload
            event_type = "culture.ritual_created"
        elif decision.action == "create_artifact":
            key = self._unique_key(
                world.culture["artifacts"],
                f"sc-a{world.colony_day:03d}-{_slug(decision.data['title'])}",
                world,
            )
            payload = {
                "artifact_id": key,
                "title": decision.data["title"],
                "artifact_type": decision.data["artifact_type"],
                "content": decision.data["content"],
                "author": citizen.citizen_id,
                "day": world.colony_day,
                "review_status": "pending",
            }
            world.culture["artifacts"][key] = payload
            world.review_queue.append(key)
            event_type = "artifact.review_requested"
        else:  # pragma: no cover - parser makes this unreachable
            raise DecisionValidationError(f"unsupported action: {decision.action}")

        world.ledger.append(
            colony_day=world.colony_day,
            event_type=event_type,
            actor_id=citizen.citizen_id,
            payload=payload,
        )

    def _apply_scheduled_intervention(self, world: World) -> str | None:
        intervention = world.config.interventions.get(world.colony_day)
        if intervention is None:
            return None
        if intervention == "responsive_seal":
            world.artifacts["responsive-seal"] = Artifact(
                artifact_id="responsive-seal",
                region_id="origin",
                artifact_type="responsive_seal",
                discovered=True,
            )
        world.ledger.append(
            colony_day=world.colony_day,
            event_type="creator.intervention",
            actor_id="creator",
            payload={"intervention": intervention, "scheduled": True},
        )
        return intervention

    def advance_one_day(self) -> TurnReport:
        if self.store.is_paused():
            raise RuntimeError("colony clock is paused")
        world = self.store.load()
        living = [citizen for citizen in world.citizens.values() if citizen.alive]

        parsed: list[tuple[Citizen, CitizenDecision]] = []
        for citizen in living:
            prompt = build_citizen_prompt(world, citizen)
            raw = self.decision_provider(prompt, citizen.citizen_id)
            parsed.append((citizen, CitizenDecision.from_json(raw)))

        world.colony_day += 1
        world.ledger.append(
            colony_day=world.colony_day,
            event_type="day.started",
            actor_id="kernel",
            payload={"living_citizens": len(living)},
        )
        for citizen, decision in parsed:
            if citizen.alive:
                self._apply_decision(world, citizen, decision)

        intervention = self._apply_scheduled_intervention(world)
        world.ledger.append(
            colony_day=world.colony_day,
            event_type="day.closed",
            actor_id="kernel",
            payload={
                "decisions_applied": len(parsed),
                "living_citizens": sum(1 for item in world.citizens.values() if item.alive),
                "review_queue_size": len(world.review_queue),
            },
        )
        self.store.save(world)
        return TurnReport(
            colony_day=world.colony_day,
            decisions_applied=len(parsed),
            living_citizens=sum(1 for item in world.citizens.values() if item.alive),
            state_digest=world.state_digest(),
            ledger_tip=world.ledger.events[-1].event_digest,
            scheduled_intervention=intervention,
        )
