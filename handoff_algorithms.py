"""
RoamWise — Wi-Fi Handoff Decision Algorithms
--------------------------------------------
This module implements three switching strategies:
1. BasicSignalHandoff: Greedy, RSSI-only switching (classic naive approach).
2. PersistenceHandoff: Fixed hysteresis + dwell time (time-to-trigger).
3. RoamWiseHandoff: Adaptive threshold based on signal fluctuation (standard deviation)
   + cross-layer QoS quality evaluation + emergency fast-roam + ping-pong suppression.

Design Rationale (For Viva):
- In mobile wireless networks, the decision to hand off (roam) from one Access Point
  to another is critical.
- Naive algorithms suffer from the "Ping-Pong Effect" (excessive rapid back-and-forth
  switching between APs at boundary regions), which degrades TCP throughput, introduces
  packet drops, and wastes airtime.
- RoamWise solves this using real-time signal statistical variance (adaptive hysteresis)
  and cross-layer network health telemetry.
"""

from abc import ABC, abstractmethod
from collections import deque
import statistics
from typing import Dict, Any, Tuple, Optional, List


class BaseHandoffAlgorithm(ABC):
    """
    Abstract base class for all Wi-Fi handoff switching strategies.
    """
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def decide(
        self,
        current_ap_id: str,
        ap_measurements: Dict[str, Dict[str, Any]],
        step: int
    ) -> Tuple[str, str, Dict[str, Any]]:
        """
        Evaluate visible APs and make a roaming decision.

        Args:
            current_ap_id: Identifier of the currently associated AP.
            ap_measurements: Dict mapping ap_id -> measurement dict (rssi, latency, load, loss).
            step: Current simulation time step index.

        Returns:
            Tuple[str, str, Dict[str, Any]]:
                - target_ap_id: The AP the client should be connected to after this step.
                - reason: Short human-readable explanation of why this decision was made.
                - telemetry: Detailed algorithm metadata for plotting and viva inspection.
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset internal state, counters, and history between runs."""
        pass


class BasicSignalHandoff(BaseHandoffAlgorithm):
    """
    Strategy 1: Basic (Greedy) RSSI Switching.
    
    Rule:
    At each step, look at the RSSI of all visible APs. If any AP has a stronger
    signal than the current AP (by even a small epsilon), switch to it immediately.
    
    Academic Weakness (Viva Highlight):
    - Completely sensitive to multipath fading noise.
    - Triggers excessive ping-pong handoffs when standing near coverage overlap boundaries.
    """
    def __init__(self, margin_dbm: float = 0.0):
        super().__init__(
            name="Basic (Signal-Only)",
            description="Greedy RSSI-based roaming. Switches as soon as any AP has higher RSSI."
        )
        self.margin_dbm = margin_dbm

    def decide(
        self,
        current_ap_id: str,
        ap_measurements: Dict[str, Dict[str, Any]],
        step: int
    ) -> Tuple[str, str, Dict[str, Any]]:
        current_meas = ap_measurements.get(current_ap_id)
        current_rssi = current_meas["rssi_dbm"] if current_meas else -999.0

        # Find AP with highest RSSI
        best_ap_id = current_ap_id
        best_rssi = current_rssi

        for ap_id, meas in ap_measurements.items():
            if meas["rssi_dbm"] > best_rssi + self.margin_dbm:
                best_rssi = meas["rssi_dbm"]
                best_ap_id = ap_id

        if best_ap_id != current_ap_id:
            reason = f"Greedy switch: {best_ap_id} ({best_rssi:.1f} dBm) > {current_ap_id} ({current_rssi:.1f} dBm)"
        else:
            reason = f"Maintained {current_ap_id} (Strongest: {current_rssi:.1f} dBm)"

        telemetry = {
            "current_ap": current_ap_id,
            "target_ap": best_ap_id,
            "current_rssi": current_rssi,
            "best_rssi": best_rssi,
            "decision": "SWITCH" if best_ap_id != current_ap_id else "STAY"
        }
        return best_ap_id, reason, telemetry

    def reset(self) -> None:
        pass


class PersistenceHandoff(BaseHandoffAlgorithm):
    """
    Strategy 2: Persistence-Based Switching (Fixed Hysteresis + Dwell Time / Time-To-Trigger).
    
    Rule:
    A candidate AP must have an RSSI at least `hysteresis_dbm` higher than the current AP,
    AND this condition must persist continuously for `dwell_steps` consecutive measurements.
    
    Academic Note (Viva Highlight):
    - Standard approach in early cellular and Wi-Fi networks (IEEE 802.11 standards).
    - Reduces ping-pong, but uses static parameters. If the mobile client enters a dead zone,
      waiting for dwell steps delays the handoff, risking connection drop.
    - Also ignores network congestion and channel load.
    """
    def __init__(self, hysteresis_dbm: float = 3.0, dwell_steps: int = 3):
        super().__init__(
            name="Persistence-Based (Fixed Hysteresis)",
            description=f"Switches only when a candidate AP is >{hysteresis_dbm} dBm better for {dwell_steps} consecutive steps."
        )
        self.hysteresis_dbm = hysteresis_dbm
        self.dwell_steps = dwell_steps
        self.candidate_ap_id: Optional[str] = None
        self.consecutive_count: int = 0

    def decide(
        self,
        current_ap_id: str,
        ap_measurements: Dict[str, Dict[str, Any]],
        step: int
    ) -> Tuple[str, str, Dict[str, Any]]:
        current_meas = ap_measurements.get(current_ap_id)
        current_rssi = current_meas["rssi_dbm"] if current_meas else -999.0

        # Find the best candidate that satisfies the fixed hysteresis margin
        best_candidate: Optional[str] = None
        best_candidate_rssi = current_rssi + self.hysteresis_dbm

        for ap_id, meas in ap_measurements.items():
            if ap_id != current_ap_id:
                if meas["rssi_dbm"] > best_candidate_rssi:
                    best_candidate = ap_id
                    best_candidate_rssi = meas["rssi_dbm"]

        # Track persistence
        if best_candidate is not None:
            if best_candidate == self.candidate_ap_id:
                self.consecutive_count += 1
            else:
                self.candidate_ap_id = best_candidate
                self.consecutive_count = 1
        else:
            # Condition broken, reset counter
            self.candidate_ap_id = None
            self.consecutive_count = 0

        # Check if threshold reached
        if self.candidate_ap_id and self.consecutive_count >= self.dwell_steps:
            target_ap = self.candidate_ap_id
            reason = (f"Persistent switch to {target_ap}: maintained +{self.hysteresis_dbm} dBm "
                      f"margin for {self.consecutive_count} consecutive steps")
            # Reset after successful switch
            self.candidate_ap_id = None
            self.consecutive_count = 0
            decision = "SWITCH"
        else:
            target_ap = current_ap_id
            if self.candidate_ap_id:
                reason = (f"Candidate {self.candidate_ap_id} qualifies ({self.consecutive_count}/{self.dwell_steps} "
                          f"steps, waiting for persistence)")
                decision = "PERSISTING"
            else:
                reason = f"Maintained {current_ap_id} (No candidate exceeds +{self.hysteresis_dbm} dBm margin)"
                decision = "STAY"

        telemetry = {
            "current_ap": current_ap_id,
            "target_ap": target_ap,
            "candidate_ap": self.candidate_ap_id,
            "persistence_counter": self.consecutive_count,
            "dwell_steps_required": self.dwell_steps,
            "hysteresis_dbm": self.hysteresis_dbm,
            "decision": decision
        }
        return target_ap, reason, telemetry

    def reset(self) -> None:
        self.candidate_ap_id = None
        self.consecutive_count = 0


class RoamWiseHandoff(BaseHandoffAlgorithm):
    """
    Strategy 3: RoamWise (Adaptive Hysteresis & Stability-Aware Handoff).
    
    Key Innovations / Academic Contributions for Viva:
    1. Adaptive Hysteresis:
       Monitors recent signal fluctuation (moving standard deviation σ_RSSI over sliding window W).
       Margin = Base_Margin + α * σ_RSSI
       When signals fluctuate heavily (noisy boundary), margin widens automatically to suppress ping-pong.
       When signal is calm, margin narrows for responsive switching.
       
    2. Multi-Metric Health / Quality Score (Q_AP):
       Unlike pure RSSI, RoamWise computes a cross-layer health score considering:
       - RSSI (normalized signal strength)
       - Latency (responsiveness)
       - Congestion / Channel Load (airtime saturation)
       - Packet Loss Rate
       
    3. Emergency Fast-Roam Override:
       If current connection drops below critical survival threshold (e.g. RSSI < -82 dBm or Loss > 20%),
       it bypasses the persistence wait and switches immediately to the healthiest AP.
       
    4. Anti-Ping-Pong Memory:
       Applies a temporary dampening penalty if trying to bounce back to an AP abandoned within
       the last `cooldown_steps` steps.
    """
    def __init__(
        self,
        base_hysteresis_dbm: float = 2.5,
        fluctuation_alpha: float = 1.2,
        window_size: int = 5,
        dwell_steps: int = 2,
        emergency_rssi_cutoff: float = -82.0,
        cooldown_steps: int = 4
    ):
        super().__init__(
            name="RoamWise (Adaptive & Stability-Aware)",
            description="Dynamically adapts hysteresis based on signal standard deviation + evaluates cross-layer QoS."
        )
        self.base_hysteresis_dbm = base_hysteresis_dbm
        self.fluctuation_alpha = fluctuation_alpha
        self.window_size = window_size
        self.dwell_steps = dwell_steps
        self.emergency_rssi_cutoff = emergency_rssi_cutoff
        self.cooldown_steps = cooldown_steps

        # Internal history structures
        self.rssi_history: Dict[str, deque] = {}
        self.candidate_ap_id: Optional[str] = None
        self.consecutive_count: int = 0
        self.last_handoff_step: int = -99
        self.previous_ap_id: Optional[str] = None

    def _update_history(self, ap_measurements: Dict[str, Dict[str, Any]]) -> None:
        for ap_id, meas in ap_measurements.items():
            if ap_id not in self.rssi_history:
                self.rssi_history[ap_id] = deque(maxlen=self.window_size)
            self.rssi_history[ap_id].append(meas["rssi_dbm"])

    def _calculate_signal_std(self, ap_id: str) -> float:
        """Calculates standard deviation of recent RSSI measurements for an AP."""
        hist = self.rssi_history.get(ap_id, [])
        if len(hist) < 2:
            return 0.5 # default nominal std
        return statistics.stdev(hist)

    @staticmethod
    def calculate_quality_score(meas: Dict[str, Any]) -> float:
        """
        Calculates a composite Quality Score Q in [0.0, 1.0] from cross-layer metrics:
        Q = 0.45 * NormRSSI + 0.20 * NormLatency + 0.20 * NormLoad + 0.15 * NormLoss
        """
        # 1. RSSI component (-95 dBm -> 0.0, -45 dBm -> 1.0)
        norm_rssi = max(0.0, min(1.0, (meas["rssi_dbm"] - (-95.0)) / 50.0))

        # 2. Latency component (10ms -> 1.0, 100ms -> 0.0)
        norm_lat = max(0.0, min(1.0, 1.0 - (meas["latency_ms"] - 5.0) / 95.0))

        # 3. Channel load component (0.0 load -> 1.0, 1.0 load -> 0.0)
        norm_load = max(0.0, min(1.0, 1.0 - meas.get("load_factor", 0.2)))

        # 4. Packet loss component (0% loss -> 1.0, 30% loss -> 0.0)
        norm_loss = max(0.0, min(1.0, 1.0 - (meas.get("packet_loss_rate", 0.0) / 0.30)))

        q = (0.35 * norm_rssi) + (0.25 * norm_lat) + (0.25 * norm_load) + (0.15 * norm_loss)
        return round(q, 3)

    def decide(
        self,
        current_ap_id: str,
        ap_measurements: Dict[str, Dict[str, Any]],
        step: int
    ) -> Tuple[str, str, Dict[str, Any]]:
        self._update_history(ap_measurements)
        current_meas = ap_measurements.get(current_ap_id)
        current_rssi = current_meas["rssi_dbm"] if current_meas else -999.0
        current_q = self.calculate_quality_score(current_meas) if current_meas else 0.0

        # Compute signal standard deviation of the current AP
        curr_std = self._calculate_signal_std(current_ap_id)

        # Dynamic Adaptive Hysteresis Margin:
        # High fluctuation -> margin automatically expands!
        adaptive_margin = round(self.base_hysteresis_dbm + (self.fluctuation_alpha * curr_std), 2)

        # Emergency Fast-Roam Check:
        # If current signal is critical or suffering extreme packet loss, don't wait!
        is_emergency = False
        if current_meas and (current_rssi < self.emergency_rssi_cutoff or current_meas.get("packet_loss_rate", 0.0) > 0.22):
            is_emergency = True

        # Find best candidate by Quality Score and RSSI
        best_candidate: Optional[str] = None
        best_candidate_score = -1.0
        best_candidate_rssi = -999.0
        best_candidate_is_qos = False

        for ap_id, meas in ap_measurements.items():
            if ap_id == current_ap_id:
                continue

            cand_score = self.calculate_quality_score(meas)
            cand_rssi = meas["rssi_dbm"]

            # Anti-ping-pong penalty if candidate is the one we JUST deserted within cooldown steps
            in_cooldown = (
                self.previous_ap_id == ap_id and
                (step - self.last_handoff_step) < self.cooldown_steps
            )
            effective_margin = adaptive_margin + (3.0 if in_cooldown else 0.0)

            # Check eligibility:
            if is_emergency:
                # In emergency, any AP with meaningfully better RSSI or higher quality is accepted immediately
                if cand_score > current_q and cand_rssi > current_rssi + 2.0:
                    if cand_score > best_candidate_score:
                        best_candidate = ap_id
                        best_candidate_score = cand_score
                        best_candidate_rssi = cand_rssi
                        best_candidate_is_qos = False
            else:
                # Normal condition:
                # Condition 1: Signal-Driven Roam (higher RSSI by adaptive margin + superior quality)
                is_signal_better = (cand_rssi > current_rssi + effective_margin) and (cand_score > current_q + 0.05)

                # Condition 2: Cross-Layer QoS Offload Roam
                # (When current AP has severe load/congestion/latency, and candidate has viable signal >= -75 dBm and notably better quality)
                is_current_degraded = (
                    (current_meas.get("load_factor", 0.0) >= 0.55) or
                    (current_meas.get("packet_loss_rate", 0.0) >= 0.06) or
                    (current_meas.get("latency_ms", 0.0) >= 35.0) or
                    (current_q < 0.60)
                )
                has_viable_signal = (cand_rssi >= -75.0)
                is_qos_better = (
                    is_current_degraded and
                    has_viable_signal and
                    (cand_score > current_q + 0.10) and
                    (not in_cooldown)
                )

                if is_signal_better or is_qos_better:
                    if cand_score > best_candidate_score:
                        best_candidate = ap_id
                        best_candidate_score = cand_score
                        best_candidate_rssi = cand_rssi
                        best_candidate_is_qos = is_qos_better and not is_signal_better

        # Decision Execution:
        if is_emergency and best_candidate:
            # Immediate Emergency Roam!
            target_ap = best_candidate
            reason = (f"EMERGENCY Fast-Roam to {target_ap}: current {current_ap_id} degraded "
                      f"(RSSI={current_rssi:.1f} dBm, Loss={current_meas.get('packet_loss_rate',0)*100:.1f}%)")
            self.previous_ap_id = current_ap_id
            self.last_handoff_step = step
            self.candidate_ap_id = None
            self.consecutive_count = 0
            decision = "EMERGENCY_SWITCH"

        elif best_candidate:
            # Persistent dwell check with adaptive margin
            if best_candidate == self.candidate_ap_id:
                self.consecutive_count += 1
            else:
                self.candidate_ap_id = best_candidate
                self.consecutive_count = 1

            if self.consecutive_count >= self.dwell_steps:
                target_ap = self.candidate_ap_id
                if best_candidate_is_qos:
                    reason = (f"Cross-Layer QoS Offload to {target_ap}: avoided congestion on {current_ap_id} "
                              f"(Load {current_meas.get('load_factor',0)*100:.0f}%, Quality {best_candidate_score:.2f} > {current_q:.2f})")
                else:
                    reason = (f"Smart switch to {target_ap}: exceeded adaptive margin (+{adaptive_margin:.1f} dBm, "
                              f"σ={curr_std:.2f} dB) & Quality {best_candidate_score:.2f} > {current_q:.2f} "
                              f"for {self.consecutive_count} steps")
                self.previous_ap_id = current_ap_id
                self.last_handoff_step = step
                self.candidate_ap_id = None
                self.consecutive_count = 0
                decision = "SMART_SWITCH"
            else:
                target_ap = current_ap_id
                reason = (f"Candidate {self.candidate_ap_id} qualifies "
                          f"({self.consecutive_count}/{self.dwell_steps} steps, stabilizing)")
                decision = "STABILIZING"
        else:
            self.candidate_ap_id = None
            self.consecutive_count = 0
            target_ap = current_ap_id
            reason = (f"Maintained {current_ap_id}: stable (σ={curr_std:.2f} dB, adaptive margin={adaptive_margin:.1f} dBm, "
                      f"Q={current_q:.2f})")
            decision = "STAY"

        telemetry = {
            "current_ap": current_ap_id,
            "target_ap": target_ap,
            "candidate_ap": self.candidate_ap_id,
            "signal_std": round(curr_std, 2),
            "adaptive_margin_dbm": adaptive_margin,
            "current_quality": current_q,
            "is_emergency": is_emergency,
            "decision": decision
        }
        return target_ap, reason, telemetry

    def reset(self) -> None:
        self.rssi_history.clear()
        self.candidate_ap_id = None
        self.consecutive_count = 0
        self.last_handoff_step = -99
        self.previous_ap_id = None
