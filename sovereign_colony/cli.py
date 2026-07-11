from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any, Sequence

from .kernel import build_experiment_001
from .model_adapter import _atomic_text_write, apply_response_batch, prepare_prompt_batch
from .persistence import SQLiteColonyStore
from .turns import CitizenDecision


def _status(store: SQLiteColonyStore) -> dict[str, Any]:
    world = store.load()
    return {
        "experiment": world.config.name,
        "colony_day": world.colony_day,
        "paused": store.is_paused(),
        "living_citizens": sum(1 for citizen in world.citizens.values() if citizen.alive),
        "total_citizens": len(world.citizens),
        "world_energy": world.world_energy,
        "total_accounted_energy": world.total_accounted_energy(),
        "review_queue_size": len(world.review_queue),
        "event_count": len(world.ledger.events),
        "event_chain_valid": world.ledger.verify_chain(),
        "state_digest": world.state_digest(),
        "ledger_tip": world.ledger.events[-1].event_digest,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sovereign-colony")
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init")
    init.add_argument("--db", required=True)
    init.add_argument("--seed", required=True, type=int)

    for name in ("status", "pause", "resume"):
        command = commands.add_parser(name)
        command.add_argument("--db", required=True)

    prepare = commands.add_parser("prepare")
    prepare.add_argument("--db", required=True)
    prepare.add_argument("--batch-root", required=True)
    prepare.add_argument("--model", default="qwen2.5:1.5b")

    apply = commands.add_parser("apply")
    apply.add_argument("--db", required=True)
    apply.add_argument("--batch-dir", required=True)

    emergency = commands.add_parser("emergency-pause")
    emergency.add_argument("--db", required=True)
    emergency.add_argument("--reason", required=True)

    validate = commands.add_parser("validate-response")
    validate.add_argument("--file", required=True)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    if arguments.command == "validate-response":
        path = Path(arguments.file)
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 16_384:
            raise ValueError("response file is missing or unsafe")
        decision = CitizenDecision.from_json(path.read_text(encoding="utf-8"))
        print(json.dumps({"valid": True, "action": decision.action}, sort_keys=True))
        return 0

    store = SQLiteColonyStore(arguments.db)
    if arguments.command == "init":
        store.initialize(build_experiment_001(seed=arguments.seed))
        result = _status(store)
    elif arguments.command == "status":
        result = _status(store)
    elif arguments.command == "pause":
        store.set_paused(True)
        result = _status(store)
    elif arguments.command == "resume":
        store.set_paused(False)
        result = _status(store)
    elif arguments.command == "prepare":
        world = store.load()
        target_day = world.colony_day + 1
        batch_dir = Path(arguments.batch_root) / f"day-{target_day:03d}"
        manifest = prepare_prompt_batch(store, batch_dir, model=arguments.model)
        result = {**manifest, "batch_dir": str(batch_dir.resolve())}
    elif arguments.command == "apply":
        batch_dir = Path(arguments.batch_dir)
        report = apply_response_batch(store, batch_dir)
        result = asdict(report)
        world = store.load()
        evidence = {
            "report": result,
            "citizens": {
                citizen_id: {
                    "name": citizen.name,
                    "energy": citizen.energy,
                    "alive": citizen.alive,
                }
                for citizen_id, citizen in sorted(world.citizens.items())
            },
            "known_regions": sorted(world.discovered_regions),
            "world_energy": world.world_energy,
            "culture": world.culture,
            "review_queue": world.review_queue,
            "event_count": len(world.ledger.events),
            "event_chain_valid": world.ledger.verify_chain(),
        }
        _atomic_text_write(
            batch_dir / "day-report.json",
            json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        )
    elif arguments.command == "emergency-pause":
        reason = arguments.reason.strip()
        if not reason or len(reason) > 500:
            raise ValueError("emergency pause reason must be 1-500 characters")
        store.set_paused(True)
        world = store.load()
        world.ledger.append(
            colony_day=world.colony_day,
            event_type="creator.emergency_pause",
            actor_id="creator",
            payload={"reason": reason},
        )
        store.save(world)
        result = _status(store)
    else:  # pragma: no cover
        raise RuntimeError(f"unsupported command: {arguments.command}")

    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
