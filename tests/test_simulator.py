"""
End-to-End Simulation Tests
"""

import unittest
from simulator import Simulator
from scenarios import create_stable_linear_walk, create_fluctuating_boundary
from handoff_algorithms import BasicSignalHandoff, PersistenceHandoff, RoamWiseHandoff


class TestSimulator(unittest.TestCase):
    def test_deterministic_trace_generation(self):
        sim1 = Simulator(seed=777)
        sim2 = Simulator(seed=777)
        scen = create_stable_linear_walk(seed=777)

        trace1 = sim1.generate_channel_trace(scen)
        trace2 = sim2.generate_channel_trace(scen)

        self.assertEqual(len(trace1), len(trace2))
        for step_i in range(len(trace1)):
            m1 = trace1[step_i]["measurements"]
            m2 = trace2[step_i]["measurements"]
            for ap_id in ["AP-1", "AP-2", "AP-3"]:
                self.assertEqual(m1[ap_id]["rssi_dbm"], m2[ap_id]["rssi_dbm"])

    def test_run_comparison_output_structure(self):
        sim = Simulator(seed=42)
        scen = create_fluctuating_boundary(seed=42)
        results = sim.run_comparison(scen)

        self.assertEqual(len(results), 3)
        for name, res in results.items():
            self.assertEqual(len(res.time_series), scen.duration_steps)
            self.assertIsNotNone(res.summary)
            self.assertGreaterEqual(res.summary.packet_delivery_ratio_pct, 0.0)
            self.assertLessEqual(res.summary.packet_delivery_ratio_pct, 100.0)

    def test_roamwise_reduces_ping_pong_compared_to_basic(self):
        # In a fluctuating boundary scenario, RoamWise should have far fewer handoffs than basic
        sim = Simulator(seed=42)
        scen = create_fluctuating_boundary(seed=42)
        results = sim.run_comparison(scen)

        basic_res = results["Basic (Signal-Only)"]
        roamwise_res = results["RoamWise (Adaptive & Stability-Aware)"]

        # Basic should have triggered significantly more handoffs due to flapping
        self.assertGreater(basic_res.summary.handoff_count, roamwise_res.summary.handoff_count)


if __name__ == "__main__":
    unittest.main()
