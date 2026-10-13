"""
Unit Tests for AccessPoint Model and Wireless Propagation
"""

import unittest
import math
import random
from access_point import AccessPoint


class TestAccessPoint(unittest.TestCase):
    def setUp(self):
        self.ap = AccessPoint(
            ap_id="AP-Test",
            ssid="RoamWise-Test",
            channel=6,
            frequency_ghz=2.4,
            tx_power_dbm=20.0,
            x=0.0,
            y=0.0,
            load_factor=0.2,
            base_latency_ms=10.0,
            base_packet_loss=0.01,
            path_loss_exponent=3.0,
            reference_loss_1m=40.0
        )

    def test_distance_calculation(self):
        # Distance to (3, 4) should be 5 meters
        dist = self.ap.distance_to(3.0, 4.0)
        self.assertAlmostEqual(dist, 5.0, places=2)

        # Distance to (0, 0) should be clamped to minimum 1.0 meter
        dist_zero = self.ap.distance_to(0.0, 0.0)
        self.assertEqual(dist_zero, 1.0)

    def test_rssi_decreases_with_distance(self):
        rng1 = random.Random(123)
        rng2 = random.Random(123)
        rssi_near = self.ap.calculate_rssi(client_x=2.0, client_y=0.0, shadow_fading_std=0.0, rng=rng1)
        rssi_far = self.ap.calculate_rssi(client_x=30.0, client_y=0.0, shadow_fading_std=0.0, rng=rng2)
        
        self.assertGreater(rssi_near, rssi_far)
        # Verify clamp boundaries
        self.assertGreaterEqual(rssi_near, -95.0)
        self.assertLessEqual(rssi_near, -30.0)
        self.assertGreaterEqual(rssi_far, -95.0)

    def test_qos_calculation(self):
        # Strong signal vs weak signal
        lat_strong, loss_strong = self.ap.calculate_qos(rssi=-40.0)
        lat_weak, loss_weak = self.ap.calculate_qos(rssi=-90.0)

        self.assertLess(lat_strong, lat_weak)
        self.assertLess(loss_strong, loss_weak)
        self.assertGreaterEqual(lat_strong, 4.0)
        self.assertLessEqual(loss_weak, 1.0)

    def test_measurement_structure(self):
        meas = self.ap.measure(client_x=10.0, client_y=10.0)
        self.assertEqual(meas["ap_id"], "AP-Test")
        self.assertIn("rssi_dbm", meas)
        self.assertIn("latency_ms", meas)
        self.assertIn("packet_loss_rate", meas)
        self.assertIn("pdr_pct", meas)
        self.assertAlmostEqual(meas["pdr_pct"], (1.0 - meas["packet_loss_rate"]) * 100.0, places=1)


if __name__ == "__main__":
    unittest.main()
