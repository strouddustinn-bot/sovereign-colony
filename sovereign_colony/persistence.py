from __future__ import annotations

from contextlib import closing
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
from typing import Any

from .kernel import (
    Artifact,
    Citizen,
    Event,
    EventLedger,
    ExperimentConfig,
    World,
)


class IntegrityError(RuntimeError):
    """Raised when persisted colony evidence cannot be verified."""


class SQLiteColonyStore:
    """Durable, fail-closed storage for one Sovereign Colony world."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    @staticmethod
    def _create_schema(connection: sqlite3.Connection) -> None:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS events (
                sequence INTEGER PRIMARY KEY,
                event_id TEXT NOT NULL UNIQUE,
                colony_day INTEGER NOT NULL CHECK (colony_day >= 0),
                event_type TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                correlation_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                resource_delta INTEGER NOT NULL,
                previous_digest TEXT NOT NULL,
                event_digest TEXT NOT NULL UNIQUE,
                kernel_version TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS snapshot (
                singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                colony_day INTEGER NOT NULL,
                world_json TEXT NOT NULL,
                state_digest TEXT NOT NULL,
                ledger_tip TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS runtime (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )

    @staticmethod
    def _event_values(event: Event) -> tuple[Any, ...]:
        return (
            event.sequence,
            event.event_id,
            event.colony_day,
            event.event_type,
            event.actor_id,
            event.correlation_id,
            EventLedger._canonical(event.payload),
            event.resource_delta,
            event.previous_digest,
            event.event_digest,
            event.kernel_version,
        )

    @classmethod
    def _insert_event(cls, connection: sqlite3.Connection, event: Event) -> None:
        connection.execute(
            """
            INSERT INTO events (
                sequence, event_id, colony_day, event_type, actor_id,
                correlation_id, payload_json, resource_delta,
                previous_digest, event_digest, kernel_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            cls._event_values(event),
        )

    @staticmethod
    def _world_payload(world: World) -> dict[str, Any]:
        return {
            "config_name": world.config.name,
            "seed": world.seed,
            "colony_day": world.colony_day,
            "citizens": {
                citizen_id: asdict(citizen)
                for citizen_id, citizen in sorted(world.citizens.items())
            },
            "artifacts": {
                artifact_id: asdict(artifact)
                for artifact_id, artifact in sorted(world.artifacts.items())
            },
            "discovered_regions": sorted(world.discovered_regions),
            "world_energy": world.world_energy,
            "dissipated_energy": world.dissipated_energy,
            "culture": world.culture,
            "review_queue": world.review_queue,
            "private_memories": world.private_memories,
        }

    @classmethod
    def _write_snapshot(cls, connection: sqlite3.Connection, world: World) -> None:
        connection.execute(
            """
            INSERT INTO snapshot (
                singleton, colony_day, world_json, state_digest, ledger_tip
            ) VALUES (1, ?, ?, ?, ?)
            ON CONFLICT(singleton) DO UPDATE SET
                colony_day = excluded.colony_day,
                world_json = excluded.world_json,
                state_digest = excluded.state_digest,
                ledger_tip = excluded.ledger_tip
            """,
            (
                world.colony_day,
                EventLedger._canonical(cls._world_payload(world)),
                world.state_digest(),
                world.ledger.events[-1].event_digest,
            ),
        )

    def initialize(self, world: World) -> None:
        if not world.ledger.verify_chain():
            raise IntegrityError("refusing to initialize from an invalid event chain")
        with closing(self._connect()) as connection, connection:
            self._create_schema(connection)
            connection.execute("BEGIN IMMEDIATE")
            count = connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            if count == 0:
                for event in world.ledger.events:
                    self._insert_event(connection, event)
                self._write_snapshot(connection, world)
                connection.execute(
                    "INSERT OR REPLACE INTO runtime (key, value) VALUES ('paused', 'true')"
                )
            else:
                row = connection.execute(
                    "SELECT world_json FROM snapshot WHERE singleton = 1"
                ).fetchone()
                if row is None:
                    raise IntegrityError("events exist without a world snapshot")
                stored = json.loads(row["world_json"])
                if stored.get("seed") != world.seed:
                    raise IntegrityError("existing colony seed does not match genesis")

    def _load_events(self, connection: sqlite3.Connection) -> list[Event]:
        rows = connection.execute("SELECT * FROM events ORDER BY sequence").fetchall()
        events = [
            Event(
                event_id=row["event_id"],
                sequence=row["sequence"],
                colony_day=row["colony_day"],
                event_type=row["event_type"],
                actor_id=row["actor_id"],
                correlation_id=row["correlation_id"],
                payload=json.loads(row["payload_json"]),
                resource_delta=row["resource_delta"],
                previous_digest=row["previous_digest"],
                event_digest=row["event_digest"],
                kernel_version=row["kernel_version"],
            )
            for row in rows
        ]
        ledger = EventLedger()
        ledger.events = events
        if not events or not ledger.verify_chain():
            raise IntegrityError("persisted event chain is invalid")
        return events

    def load(self) -> World:
        with closing(self._connect()) as connection, connection:
            self._create_schema(connection)
            events = self._load_events(connection)
            snapshot = connection.execute(
                "SELECT * FROM snapshot WHERE singleton = 1"
            ).fetchone()
            if snapshot is None:
                raise IntegrityError("world snapshot is missing")
            payload = json.loads(snapshot["world_json"])

        config = ExperimentConfig.experiment_001()
        if payload.get("config_name") != config.name:
            raise IntegrityError("snapshot experiment does not match this kernel")

        ledger = EventLedger()
        ledger.events = events
        citizens = {
            citizen_id: Citizen(
                citizen_id=value["citizen_id"],
                name=value["name"],
                talents=tuple(value["talents"]),
                tensions=tuple(value["tensions"]),
                energy=value["energy"],
                alive=value["alive"],
                born_day=value["born_day"],
                died_day=value["died_day"],
            )
            for citizen_id, value in payload["citizens"].items()
        }
        artifacts = {
            artifact_id: Artifact(**value)
            for artifact_id, value in payload["artifacts"].items()
        }
        world = World(
            config=config,
            seed=payload["seed"],
            ledger=ledger,
            citizens=citizens,
            artifacts=artifacts,
            discovered_regions=set(payload["discovered_regions"]),
            world_energy=payload["world_energy"],
            dissipated_energy=payload["dissipated_energy"],
            colony_day=payload["colony_day"],
            culture=payload.get(
                "culture",
                {"words": {}, "norms": {}, "rituals": {}, "artifacts": {}, "messages": []},
            ),
            review_queue=payload.get("review_queue", []),
            private_memories={
                citizen_id: list(notes)
                for citizen_id, notes in payload.get("private_memories", {}).items()
            },
        )
        if snapshot["ledger_tip"] != events[-1].event_digest:
            raise IntegrityError("snapshot ledger tip does not match event chain")
        if snapshot["state_digest"] != world.state_digest():
            raise IntegrityError("snapshot state digest is invalid")
        return world

    def save(self, world: World) -> None:
        if not world.ledger.verify_chain():
            raise IntegrityError("refusing to save an invalid event chain")
        with closing(self._connect()) as connection, connection:
            self._create_schema(connection)
            connection.execute("BEGIN IMMEDIATE")
            persisted = connection.execute(
                "SELECT sequence, event_digest FROM events ORDER BY sequence"
            ).fetchall()
            if len(persisted) > len(world.ledger.events):
                raise IntegrityError("in-memory ledger is behind persisted history")
            for row, event in zip(persisted, world.ledger.events):
                if row["sequence"] != event.sequence or row["event_digest"] != event.event_digest:
                    raise IntegrityError("persisted history diverges from in-memory history")
            for event in world.ledger.events[len(persisted):]:
                self._insert_event(connection, event)
            self._write_snapshot(connection, world)

    def is_paused(self) -> bool:
        with closing(self._connect()) as connection, connection:
            self._create_schema(connection)
            row = connection.execute(
                "SELECT value FROM runtime WHERE key = 'paused'"
            ).fetchone()
            return True if row is None else row["value"] == "true"

    def set_paused(self, paused: bool) -> None:
        with closing(self._connect()) as connection, connection:
            self._create_schema(connection)
            connection.execute(
                "INSERT OR REPLACE INTO runtime (key, value) VALUES ('paused', ?)",
                ("true" if paused else "false",),
            )
