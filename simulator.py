"""
RoamWise — Simulation Engine
----------------------------
This module coordinates the simulation execution:
1. Generates deterministic channel realizations from scenario definitions.
2. Evaluates handoff algorithms on the exact same channel trace for 100% fair comparison.
3. Records comprehensive step-by-step telemetry and handoff transition events.
4. Generates structured pandas DataFrames for visualization and CSV export.
"""

from typing import List, Dict, Any, Optional, Tuple
import random
import copy
from access_point import AccessPoint
from handoff_algorithms import (
    BaseHandoffAlgorithm,
    BasicSignalHandoff,
    PersistenceHandoff,
    RoamWiseHandoff
)
from scenarios import Scenario, get_all_scenarios
from metrics import (
    HandoffEvent,
    SimulationMetricsSummary,
    calculate_metrics,
    DEFAULT_HANDOFF_DISRUPTION_MS
)


class SimulationResult:
    """
    Holds complete output data for a single algorithm run.
    """
    def __init__(
        self,
        algorithm_name: str,
        scenario: Scenario,
        time_series: List[Dict[str, Any]],
        handoff_events: List[HandoffEvent],
        summary: SimulationMetricsSummary
    ):
        self.algorithm_name = algorithm_name
        self.scenario = scenario
        self.time_series = time_series
        self.handoff_events = handoff_events
        self.summary = summary


class Simulator:
    """
    The central simulation coordinator.
    """
    def __init__(self, seed: int = 42):
        self.seed = seed

    def generate_channel_trace(
        self,
        scenario: Scenario
    ) -> List[Dict[str, Any]]:
        """
        Pre-computes environmental channel measurements for every AP at every step.
        Pre-generating this trace guarantees that every algorithm evaluated on this
        scenario faces the exact same signal levels, shadow fading, and obstacles.
        """
        # Make a deep copy of access points so step events don't mutate external objects
        aps = copy.deepcopy(scenario.access_points)
        rng = random.Random(self.seed)
        trace: List[Dict[str, Any]] = []

        for step, (cx, cy) in enumerate(scenario.trajectory):
            # Apply dynamic step events if any (e.g. wall obstacle at step 28)
            if scenario.step_events and step in scenario.step_events:
                event_data = scenario.step_events[step]
                if callable(event_data):
                    event_data(aps, step)
                elif isinstance(event_data, list):
                    for mod in event_data:
                        target_id = mod.get("ap_id")
                        for ap in aps:
                            if ap.ap_id == target_id:
                                if "tx_power_dbm" in mod:
                                    ap.tx_power_dbm = mod["tx_power_dbm"]
                                if "load_factor" in mod:
                                    ap.load_factor = mod["load_factor"]

            # Measure all APs
            ap_measurements: Dict[str, Dict[str, Any]] = {}
            for ap in aps:
                meas = ap.measure(
                    client_x=cx,
                    client_y=cy,
                    shadow_fading_std=scenario.shadow_fading_std,
                    rng=rng
                )
                ap_measurements[ap.ap_id] = meas

            trace.append({
                "step": step,
                "client_x": cx,
                "client_y": cy,
                "measurements": ap_measurements
            })

        return trace

    def run_algorithm(
        self,
        algorithm: BaseHandoffAlgorithm,
        scenario: Scenario,
        precomputed_trace: Optional[List[Dict[str, Any]]] = None
    ) -> SimulationResult:
        """
        Executes a single algorithm across the scenario.
        """
        algorithm.reset()
        trace = precomputed_trace or self.generate_channel_trace(scenario)

        current_ap_id = scenario.initial_ap_id
        time_series_records: List[Dict[str, Any]] = []
        raw_handoff_events: List[HandoffEvent] = []

        for item in trace:
            step = item["step"]
            cx = item["client_x"]
            cy = item["client_y"]
            measurements = item["measurements"]

            # Algorithm makes decision
            target_ap_id, reason, telemetry = algorithm.decide(
                current_ap_id=current_ap_id,
                ap_measurements=measurements,
                step=step
            )

            is_handoff = (target_ap_id != current_ap_id)
            if is_handoff:
                raw_handoff_events.append(
                    HandoffEvent(
                        step=step,
                        from_ap=current_ap_id,
                        to_ap=target_ap_id,
                        reason=reason,
                        disruption_ms=DEFAULT_HANDOFF_DISRUPTION_MS
                    )
                )
                current_ap_id = target_ap_id

            # Active connection metrics at this step
            active_meas = measurements.get(current_ap_id)
            if not active_meas:
                # Fallback safeguard
                active_meas = list(measurements.values())[0]

            # If handoff occurred, incur transient disruption latency and loss penalty
            step_latency = active_meas["latency_ms"] + (DEFAULT_HANDOFF_DISRUPTION_MS if is_handoff else 0.0)
            step_loss = min(1.0, active_meas["packet_loss_rate"] + (0.15 if is_handoff else 0.0))
            step_pdr = round((1.0 - step_loss) * 100.0, 2)

            record = {
                "step": step,
                "time_s": step * 1.0, # each step = 1.0 second
                "client_x": cx,
                "client_y": cy,
                "connected_ap": current_ap_id,
                "rssi_dbm": active_meas["rssi_dbm"],
                "latency_ms": round(step_latency, 2),
                "packet_loss_rate": round(step_loss, 4),
                "pdr_pct": step_pdr,
                "is_handoff": is_handoff,
                "decision_reason": reason,
                # Store individual AP RSSIs for multi-line plotting
                "ap1_rssi": measurements.get("AP-1", {}).get("rssi_dbm", -95.0),
                "ap2_rssi": measurements.get("AP-2", {}).get("rssi_dbm", -95.0),
                "ap3_rssi": measurements.get("AP-3", {}).get("rssi_dbm", -95.0),
                # Telemetry
                "adaptive_margin_dbm": telemetry.get("adaptive_margin_dbm", 0.0),
                "signal_std": telemetry.get("signal_std", 0.0),
                "quality_score": telemetry.get("current_quality", 0.0),
                "decision": telemetry.get("decision", "STAY")
            }
            time_series_records.append(record)

        summary, processed_events = calculate_metrics(
            algorithm_name=algorithm.name,
            time_series_records=time_series_records,
            raw_handoff_events=raw_handoff_events
        )

        return SimulationResult(
            algorithm_name=algorithm.name,
            scenario=scenario,
            time_series=time_series_records,
            handoff_events=processed_events,
            summary=summary
        )

    def run_comparison(
        self,
        scenario: Scenario,
        algorithms: Optional[List[BaseHandoffAlgorithm]] = None
    ) -> Dict[str, SimulationResult]:
        """
        Runs all algorithms under the identical precomputed channel trace.
        """
        if algorithms is None:
            algorithms = [
                BasicSignalHandoff(),
                PersistenceHandoff(hysteresis_dbm=3.0, dwell_steps=3),
                RoamWiseHandoff(base_hysteresis_dbm=2.5, fluctuation_alpha=1.2, window_size=5)
            ]

        # Generate shared channel trace once
        shared_trace = self.generate_channel_trace(scenario)

        results: Dict[str, SimulationResult] = {}
        for algo in algorithms:
            res = self.run_algorithm(algo, scenario, precomputed_trace=shared_trace)
            results[algo.name] = res

        return results
