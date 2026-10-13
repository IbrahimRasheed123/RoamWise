"""
RoamWise — Performance Metrics and Analysis Engine
--------------------------------------------------
This module calculates key performance indicators (KPIs) to compare
Wi-Fi handoff strategies rigorously:

1. Handoff Count (Total transitions)
2. Ping-Pong Handoff Count (Rapid back-and-forth flapping within <= 5s window)
3. Packet Delivery Ratio (PDR %)
4. Average Latency (ms) and 95th Percentile Latency
5. Simulated Connection Interruption Time (ms)
6. Quality of Experience (QoE) Composite Score (1.0 to 5.0 scale)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple
import statistics


# Simulated interruption duration for an IEEE 802.11 handoff (probe + auth + re-assoc)
DEFAULT_HANDOFF_DISRUPTION_MS = 100.0


@dataclass
class HandoffEvent:
    """
    Records a single handoff occurrence.
    """
    step: int
    from_ap: str
    to_ap: str
    reason: str
    is_ping_pong: bool = False
    disruption_ms: float = DEFAULT_HANDOFF_DISRUPTION_MS


@dataclass
class SimulationMetricsSummary:
    """
    Aggregate summary metrics for a single algorithm run.
    """
    algorithm_name: str
    total_steps: int
    handoff_count: int
    ping_pong_count: int
    ping_pong_ratio_pct: float
    avg_rssi_dbm: float
    avg_latency_ms: float
    p95_latency_ms: float
    packet_delivery_ratio_pct: float
    total_interruption_time_ms: float
    stability_score_pct: float
    qoe_score: float # 1.0 to 5.0 scale


def detect_ping_pong_handoffs(
    handoff_events: List[HandoffEvent],
    window_steps: int = 5
) -> List[HandoffEvent]:
    """
    Identifies ping-pong handoffs.
    A handoff at step t from AP_B -> AP_A is marked as a Ping-Pong if
    a handoff from AP_A -> AP_B occurred at step (t - dt) where dt <= window_steps.
    """
    marked_events: List[HandoffEvent] = []
    
    for i, event in enumerate(handoff_events):
        is_pp = False
        # Look back within window_steps
        for j in range(i - 1, -1, -1):
            prev = handoff_events[j]
            if (event.step - prev.step) > window_steps:
                break
            # Check for reciprocal transition: A -> B followed by B -> A
            if prev.from_ap == event.to_ap and prev.to_ap == event.from_ap:
                is_pp = True
                break

        marked_events.append(
            HandoffEvent(
                step=event.step,
                from_ap=event.from_ap,
                to_ap=event.to_ap,
                reason=event.reason,
                is_ping_pong=is_pp,
                disruption_ms=event.disruption_ms
            )
        )

    return marked_events


def calculate_metrics(
    algorithm_name: str,
    time_series_records: List[Dict[str, Any]],
    raw_handoff_events: List[HandoffEvent],
    handoff_disruption_ms: float = DEFAULT_HANDOFF_DISRUPTION_MS,
    ping_pong_window: int = 5
) -> Tuple[SimulationMetricsSummary, List[HandoffEvent]]:
    """
    Processes time-series telemetry and handoff logs to produce aggregate metrics.
    """
    total_steps = len(time_series_records)
    if total_steps == 0:
        raise ValueError("Cannot calculate metrics on empty simulation records.")

    # 1. Process ping-pong handoffs
    handoff_events = detect_ping_pong_handoffs(raw_handoff_events, window_steps=ping_pong_window)
    handoff_count = len(handoff_events)
    ping_pong_count = sum(1 for e in handoff_events if e.is_ping_pong)
    ping_pong_ratio = (ping_pong_count / handoff_count * 100.0) if handoff_count > 0 else 0.0

    # 2. Total interruption time
    total_interruption_ms = handoff_count * handoff_disruption_ms

    # 3. Time series averages: RSSI, Latency, Packet Loss
    rssi_list = [r["rssi_dbm"] for r in time_series_records]
    latency_list = [r["latency_ms"] for r in time_series_records]
    loss_list = [r["packet_loss_rate"] for r in time_series_records]

    avg_rssi = statistics.mean(rssi_list)
    avg_lat = statistics.mean(latency_list)
    
    # 95th percentile latency (Jitter indicator)
    sorted_lat = sorted(latency_list)
    p95_idx = int(round(0.95 * (len(sorted_lat) - 1)))
    p95_lat = sorted_lat[p95_idx]

    # 4. Packet Delivery Ratio (PDR %):
    # Base channel packet delivery ratio reduced by disruption packet loss during handoffs
    base_pdr = (1.0 - statistics.mean(loss_list)) * 100.0
    
    # Each handoff causes transient dropped packets (e.g. 10 packets dropped per 100ms disruption)
    # Relative to assumed 10 packets per 1-second step:
    handoff_penalty = (handoff_count * 0.8) / (total_steps / 10.0) if total_steps > 0 else 0.0
    final_pdr = max(0.0, min(100.0, base_pdr - handoff_penalty))

    # 5. Stability Score %:
    # Based on ping-pong avoidance and low handoff disruption
    total_sim_ms = total_steps * 1000.0
    uptime_ratio = max(0.0, (total_sim_ms - total_interruption_ms) / total_sim_ms)
    pp_penalty = (ping_pong_count * 0.08)
    stability_score = max(10.0, min(100.0, (uptime_ratio - pp_penalty) * 100.0))

    # 6. Composite QoE / MOS Score (1.0 - 5.0):
    # Telecom formula: R-factor style mapping
    r_rssi = max(0.0, min(1.0, (avg_rssi - (-90.0)) / 45.0))
    r_lat = max(0.0, min(1.0, (120.0 - avg_lat) / 110.0))
    r_pdr = final_pdr / 100.0
    r_pp = max(0.0, 1.0 - (ping_pong_count * 0.15))
    
    composite_r = (0.35 * r_pdr) + (0.25 * r_lat) + (0.20 * r_rssi) + (0.20 * r_pp)
    qoe_mos = round(1.0 + (composite_r * 4.0), 2)

    summary = SimulationMetricsSummary(
        algorithm_name=algorithm_name,
        total_steps=total_steps,
        handoff_count=handoff_count,
        ping_pong_count=ping_pong_count,
        ping_pong_ratio_pct=round(ping_pong_ratio, 1),
        avg_rssi_dbm=round(avg_rssi, 2),
        avg_latency_ms=round(avg_lat, 2),
        p95_latency_ms=round(p95_lat, 2),
        packet_delivery_ratio_pct=round(final_pdr, 2),
        total_interruption_time_ms=round(total_interruption_ms, 1),
        stability_score_pct=round(stability_score, 1),
        qoe_score=qoe_mos
    )

    return summary, handoff_events
