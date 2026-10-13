"""
Unit Tests for Wi-Fi Handoff Decision Algorithms
"""

import unittest
from handoff_algorithms import (
    BasicSignalHandoff,
    PersistenceHandoff,
    RoamWiseHandoff
)


class TestHandoffAlgorithms(unittest.TestCase):
    def test_basic_handoff_switches_immediately(self):
        algo = BasicSignalHandoff(margin_dbm=0.0)
        
        # Step 0: AP-1 is best
        meas_0 = {
            "AP-1": {"rssi_dbm": -60.0, "latency_ms": 10.0, "load_factor": 0.2, "packet_loss_rate": 0.01},
            "AP-2": {"rssi_dbm": -65.0, "latency_ms": 10.0, "load_factor": 0.2, "packet_loss_rate": 0.01}
        }
        target, _, _ = algo.decide("AP-1", meas_0, step=0)
        self.assertEqual(target, "AP-1")

        # Step 1: AP-2 becomes slightly better (-59.0 > -60.0)
        meas_1 = {
            "AP-1": {"rssi_dbm": -60.0, "latency_ms": 10.0, "load_factor": 0.2, "packet_loss_rate": 0.01},
            "AP-2": {"rssi_dbm": -59.0, "latency_ms": 10.0, "load_factor": 0.2, "packet_loss_rate": 0.01}
        }
        target, _, tel = algo.decide("AP-1", meas_1, step=1)
        self.assertEqual(target, "AP-2")
        self.assertEqual(tel["decision"], "SWITCH")

    def test_persistence_requires_consecutive_steps(self):
        algo = PersistenceHandoff(hysteresis_dbm=3.0, dwell_steps=3)
        algo.reset()

        # Current AP is AP-1 at -70 dBm
        # Step 0: AP-2 is -65 dBm (+5 dBm advantage, exceeds 3.0 dBm) -> Step 1/3
        meas_0 = {
            "AP-1": {"rssi_dbm": -70.0, "latency_ms": 10.0, "load_factor": 0.2, "packet_loss_rate": 0.01},
            "AP-2": {"rssi_dbm": -65.0, "latency_ms": 10.0, "load_factor": 0.2, "packet_loss_rate": 0.01}
        }
        target, _, tel = algo.decide("AP-1", meas_0, step=0)
        self.assertEqual(target, "AP-1") # Stays!
        self.assertEqual(tel["persistence_counter"], 1)

        # Step 1: Still qualifies -> Step 2/3
        target, _, tel = algo.decide("AP-1", meas_0, step=1)
        self.assertEqual(target, "AP-1") # Still stays!
        self.assertEqual(tel["persistence_counter"], 2)

        # Step 2: Still qualifies -> Step 3/3 -> Triggers switch!
        target, _, tel = algo.decide("AP-1", meas_0, step=2)
        self.assertEqual(target, "AP-2")
        self.assertEqual(tel["decision"], "SWITCH")

    def test_persistence_resets_on_drop(self):
        algo = PersistenceHandoff(hysteresis_dbm=3.0, dwell_steps=3)
        algo.reset()

        meas_better = {
            "AP-1": {"rssi_dbm": -70.0, "latency_ms": 10.0, "load_factor": 0.2, "packet_loss_rate": 0.01},
            "AP-2": {"rssi_dbm": -65.0, "latency_ms": 10.0, "load_factor": 0.2, "packet_loss_rate": 0.01}
        }
        meas_worse = {
            "AP-1": {"rssi_dbm": -70.0, "latency_ms": 10.0, "load_factor": 0.2, "packet_loss_rate": 0.01},
            "AP-2": {"rssi_dbm": -71.0, "latency_ms": 10.0, "load_factor": 0.2, "packet_loss_rate": 0.01}
        }

        # Step 0: qualifies
        algo.decide("AP-1", meas_better, step=0)
        # Step 1: drops below margin -> counter should reset
        _, _, tel = algo.decide("AP-1", meas_worse, step=1)
        self.assertEqual(tel["persistence_counter"], 0)
        self.assertIsNone(tel["candidate_ap"])

    def test_roamwise_emergency_fast_roam(self):
        algo = RoamWiseHandoff(emergency_rssi_cutoff=-82.0)
        algo.reset()

        # AP-1 drops into critical zone (-85 dBm)
        meas_emergency = {
            "AP-1": {"rssi_dbm": -85.0, "latency_ms": 50.0, "load_factor": 0.2, "packet_loss_rate": 0.25},
            "AP-2": {"rssi_dbm": -65.0, "latency_ms": 10.0, "load_factor": 0.2, "packet_loss_rate": 0.01}
        }
        target, _, tel = algo.decide("AP-1", meas_emergency, step=0)
        self.assertEqual(target, "AP-2")
        self.assertTrue(tel["is_emergency"])
        self.assertEqual(tel["decision"], "EMERGENCY_SWITCH")

    def test_roamwise_cross_layer_avoids_congested_ap(self):
        algo = RoamWiseHandoff()
        algo.reset()

        # AP-1 has slightly stronger RSSI (-60 dBm vs -66 dBm)
        # BUT AP-1 is 90% loaded with 80ms latency and 18% packet loss!
        meas_congested = {
            "AP-1": {"rssi_dbm": -60.0, "latency_ms": 80.0, "load_factor": 0.90, "packet_loss_rate": 0.18},
            "AP-2": {"rssi_dbm": -66.0, "latency_ms": 10.0, "load_factor": 0.10, "packet_loss_rate": 0.005}
        }
        q1 = RoamWiseHandoff.calculate_quality_score(meas_congested["AP-1"])
        q2 = RoamWiseHandoff.calculate_quality_score(meas_congested["AP-2"])
        
        # AP-2 quality must be significantly better than congested AP-1
        self.assertGreater(q2, q1)


if __name__ == "__main__":
    unittest.main()
