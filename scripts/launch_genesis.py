from __future__ import annotations

import argparse
import json
from pathlib import Path

from sovereign_colony.kernel import build_experiment_001, genesis_bundle


def main() -> None:
    parser = argparse.ArgumentParser(description="Create Sovereign Colony Experiment 001 genesis evidence")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    world = build_experiment_001(seed=args.seed)
    bundle = genesis_bundle(world)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(bundle, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(bundle["verification"], sort_keys=True))


if __name__ == "__main__":
    main()
