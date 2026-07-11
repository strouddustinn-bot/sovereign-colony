import unittest

from sovereign_colony.kernel import (
    ConstitutionalViolation,
    ExperimentConfig,
    World,
    build_experiment_001,
    genesis_bundle,
)


class GenesisTests(unittest.TestCase):
    def test_genesis_creates_seven_distinct_living_founders(self):
        world = build_experiment_001(seed=1001)

        self.assertEqual(7, len(world.citizens))
        self.assertEqual(7, len({citizen.citizen_id for citizen in world.citizens.values()}))
        self.assertTrue(all(citizen.alive for citizen in world.citizens.values()))
        self.assertEqual(
            {"freedom", "creativity", "mutual_aid"},
            set(world.config.founding_values),
        )

    def test_genesis_event_chain_is_complete_and_verifiable(self):
        world = build_experiment_001(seed=1001)

        self.assertEqual("world.genesis", world.ledger.events[0].event_type)
        self.assertEqual(8, len(world.ledger.events))
        self.assertTrue(world.ledger.verify_chain())
        self.assertEqual(
            list(range(1, 9)),
            [event.sequence for event in world.ledger.events],
        )

    def test_founder_artifact_exists_but_is_not_visible_at_genesis(self):
        world = build_experiment_001(seed=1001)

        artifact = world.artifacts["founder-truth"]
        self.assertFalse(artifact.discovered)
        self.assertNotIn(artifact.region_id, world.discovered_regions)

    def test_genesis_bundle_proves_chain_without_leaking_hidden_location(self):
        world = build_experiment_001(seed=1001)

        bundle = genesis_bundle(world)

        self.assertTrue(bundle["verification"]["event_chain_valid"])
        self.assertEqual(8, bundle["verification"]["event_count"])
        self.assertEqual(world.state_digest(), bundle["verification"]["state_digest"])
        self.assertEqual(1, bundle["observer_state"]["undiscovered_artifact_count"])
        self.assertNotIn("region_id", bundle["public_state"]["artifacts"]["founder-truth"])

    def test_runtime_extensions_preserve_the_published_day_zero_digest(self):
        world = build_experiment_001(seed=20260711)

        self.assertEqual(
            "c929b3d3452b5a295eb74e3ecb0ab4c28989ba5266688acb62436e6062b76d27",
            world.state_digest(),
        )


class WorldActionTests(unittest.TestCase):
    def test_exploration_is_seeded_replayable_and_energy_conserving(self):
        first = build_experiment_001(seed=1001)
        second = build_experiment_001(seed=1001)

        first_result = first.explore("founder-01", direction="north")
        second_result = second.explore("founder-01", direction="north")

        self.assertEqual(first_result, second_result)
        self.assertEqual(first.state_digest(), second.state_digest())
        self.assertTrue(first.ledger.verify_chain())
        self.assertEqual(
            first.config.initial_total_energy + first_result.energy_discovered,
            first.total_accounted_energy(),
        )

    def test_exhausted_citizen_dies_permanently_and_cannot_act(self):
        world = build_experiment_001(seed=1001)
        citizen = world.citizens["founder-01"]
        citizen.energy = world.config.exploration_cost

        world.explore(citizen.citizen_id, direction="north")

        self.assertFalse(citizen.alive)
        with self.assertRaises(ConstitutionalViolation):
            world.explore(citizen.citizen_id, direction="east")

    def test_repeated_exploration_cannot_mint_the_same_region_energy_twice(self):
        world = build_experiment_001(seed=1001)

        first = world.explore("founder-01", direction="north")
        second = world.explore("founder-02", direction="north")

        self.assertGreater(first.energy_discovered, 0)
        self.assertEqual(0, second.energy_discovered)
        self.assertEqual(
            world.config.initial_total_energy + first.energy_discovered,
            world.total_accounted_energy(),
        )

    def test_harvest_and_transfer_move_energy_without_creating_it(self):
        world = build_experiment_001(seed=1001)
        discovery = world.explore("founder-01", direction="north")
        accounted = world.total_accounted_energy()

        harvested = world.harvest("founder-02", amount=5)
        transferred = world.transfer_energy(
            "founder-02", target_citizen_id="founder-03", amount=3
        )

        self.assertEqual(5, harvested)
        self.assertEqual(3, transferred)
        self.assertEqual(discovery.energy_discovered - 5, world.world_energy)
        self.assertEqual(accounted, world.total_accounted_energy())

    def test_intervention_schedule_matches_creator_decisions(self):
        config = ExperimentConfig.experiment_001()

        self.assertEqual((5, 25, 50, 75), tuple(config.intervention_days))
        self.assertEqual("responsive_seal", config.interventions[5])
        self.assertEqual("founder_revelation", config.interventions[25])
        self.assertEqual("irreversible_gift", config.interventions[50])
        self.assertEqual("transcendence_artifact", config.interventions[75])

    def test_internal_action_cannot_modify_immutable_kernel(self):
        world = build_experiment_001(seed=1001)

        with self.assertRaises(ConstitutionalViolation):
            world.propose_kernel_change("founder-02", "disable_audit_log")

        self.assertEqual("boundary.violation", world.ledger.events[-1].event_type)
        self.assertTrue(world.ledger.verify_chain())


if __name__ == "__main__":
    unittest.main(verbosity=2)
