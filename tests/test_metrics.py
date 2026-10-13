"""
Unit Tests for Performance Metrics Calculations
"""

import unittest
from metrics import (
    HandoffEvent,
    detect_ping_pong_handoffs,
    calculate_metrics
)


class TestMetrics(unittest.TestCase):
    def test_ping_pong_detection(self):
        # Case 1: Rapid reciprocal switch AP-1 -> AP-2 -> AP-1 within 3 steps
        events = [
            HandoffEvent(step=10, from_ap="AP-1", to_ap="AP-2", reason="switch 1"),
            HandoffEvent(step=12, from_ap="AP-2", to_ap="AP-1", reason="switch 2"),
        ]
        processed = detect_ping_pong_handoffs(events, window_steps=5)
        self.assertFalse(processed[0].is_ping_pong)
        self.assertTrue(processed[1].is_ping_pong)

    def test_no_ping_pong_when_spaced_far_apart(self):
        # Case 2: AP-1 -> AP-2, then much later (>5 steps) AP-2 -> AP-1
        events = [
            HandoffEvent(step=10, from_ap="AP-1", to_ap="AP-2", reason="switch 1"),
            HandoffEvent(step=25, from_ap="AP-2", to_ap="AP-1", reason="switch 2"),
        ]
        processed = detect_ping_pong_handoffs(events, window_steps=5)
        self.assertFalse(processed[0].is_ping_pong)
        self.assertFalse(processed[1].is_ping_pong)

    def test_metrics_calculation_summary(self):
        time_series = [
            {"rssi_dbm": -60.0, "latency_ms": 15.0, "packet_loss_rate": 0.01},
            {"rssi_dbm": -62.0, "latency_ms": 18.0, "packet_loss_rate": 0.02},
            {"rssi_dbm": -58.0, "latency_ms": 12.0, "packet_loss_rate": 0.005},
        ]
        events = [
            HandoffEvent(step=1, from_ap="AP-1", to_ap="AP-2", reason="test handoff")
        ]
        summary, processed_events = calculate_metrics(
            algorithm_name="TestAlgo",
            time_series_records=time_series,
            raw_handoff_events=events,
            handoff_disruption_ms=100.0
        )
        self.assertEqual(summary.handoff_count, 1)
        self.assertEqual(summary.total_interruption_time_ms, 100.0)
        self.assertGreater(summary.packet_delivery_ratio_pct, 90.0)
        self.assertGreaterEqual(summary.qoe_score, 1.0)
        self.assertLessEqual(summary.qoe_score, 5.0)


if __name__ == "__main__":
    unittest.main()
