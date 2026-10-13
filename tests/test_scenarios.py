"""
Unit Tests for Scenarios and Trajectories
"""

import unittest
from scenarios import (
    get_all_scenarios,
    create_stable_linear_walk,
    create_fluctuating_boundary,
    create_deteriorating_connection,
    create_congested_hotspot,
    create_custom_scenario
)


class TestScenarios(unittest.TestCase):
    def test_all_predefined_scenarios_exist(self):
        scenarios = get_all_scenarios(seed=42)
        expected_keys = [
            "stable_linear_walk",
            "fluctuating_boundary",
            "deteriorating_connection",
            "congested_hotspot"
        ]
        for key in expected_keys:
            self.assertIn(key, scenarios)
            scen = scenarios[key]
            self.assertEqual(len(scen.access_points), 3)
            self.assertEqual(len(scen.trajectory), scen.duration_steps)
            self.assertGreater(scen.duration_steps, 0)
            self.assertGreater(scen.shadow_fading_std, 0.0)

    def test_reproducibility_with_seed(self):
        scen1 = create_fluctuating_boundary(seed=100)
        scen2 = create_fluctuating_boundary(seed=100)
        scen3 = create_fluctuating_boundary(seed=200)

        # Same seed must yield identical trajectories
        self.assertEqual(scen1.trajectory, scen2.trajectory)
        # Different seed should yield different trajectories
        self.assertNotEqual(scen1.trajectory, scen3.trajectory)

    def test_custom_scenario_generation(self):
        custom = create_custom_scenario(
            duration_steps=40,
            client_speed_mps=1.5,
            shadow_fading_std=2.5,
            ap1_load=0.1,
            ap2_load=0.2,
            ap3_load=0.3
        )
        self.assertEqual(custom.duration_steps, 40)
        self.assertEqual(len(custom.trajectory), 40)
        self.assertEqual(custom.access_points[0].load_factor, 0.1)


if __name__ == "__main__":
    unittest.main()
