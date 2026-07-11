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
