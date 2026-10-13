"""
RoamWise — Wi-Fi Access Point and Wireless Propagation Model
-----------------------------------------------------------
This module models a physical Wi-Fi Access Point (AP) and the wireless channel
physics according to standard IEEE 802.11 indoor propagation models (Log-Distance Path Loss).

Key Concepts for Students / Faculty Viva:
- Transmit Power (Tx Power): Power with which the AP transmits, typically 15-20 dBm for indoor APs.
- Path Loss: Loss of signal attenuation as distance increases, modeled logarithmically.
- Shadow Fading: Signal variations caused by obstacles/walls, modeled as a zero-mean Gaussian variable.
- RSSI (Received Signal Strength Indicator): The power measured at the mobile device in dBm (negative number; closer to 0 is stronger).
- Channel Load / Congestion: Ratio of channel airtime utilization (0.0 to 1.0).
"""

from dataclasses import dataclass, field
import math
import random
from typing import Tuple, Dict, Any, Optional


@dataclass
class AccessPoint:
    """
    Represents an IEEE 802.11 Wi-Fi Access Point.
    """
    ap_id: str                      # Unique identifier, e.g. "AP-1"
    ssid: str                       # Network identifier, e.g. "RoamWise-Mesh"
    channel: int                    # Wi-Fi channel, e.g. 1, 6, 11 (2.4 GHz) or 36, 44 (5 GHz)
    frequency_ghz: float            # Frequency in GHz (2.4 or 5.0)
    tx_power_dbm: float             # Transmit power in dBm (default: 20.0 dBm)
    x: float                        # X-coordinate in meters
    y: float                        # Y-coordinate in meters
    load_factor: float = 0.2        # Channel utilization / congestion (0.0 = idle, 1.0 = saturated)
    base_latency_ms: float = 8.0    # Baseline ping/processing latency in ms
    base_packet_loss: float = 0.005 # Baseline packet loss rate (0.5%)
    path_loss_exponent: float = 2.8 # Environmental exponent (2.0 = free space, 2.8 - 3.5 = office/indoor)
    reference_loss_1m: float = 40.0 # Path loss at d0 = 1m in dB (approx 40 dB for 2.4 GHz)

    def distance_to(self, client_x: float, client_y: float) -> float:
        """
        Calculates Euclidean distance between AP and client in meters.
        Enforces a minimum distance of 1.0 meter to avoid singularity at d=0.
        """
        dx = self.x - client_x
        dy = self.y - client_y
        dist = math.hypot(dx, dy)
        return max(1.0, dist)

    def calculate_rssi(
        self,
        client_x: float,
        client_y: float,
        shadow_fading_std: float = 1.5,
        rng: Optional[random.Random] = None
    ) -> float:
        """
        Calculates Received Signal Strength Indicator (RSSI) in dBm using the
        standard Log-Distance Path Loss Model with Shadow Fading:

            PL(d) = PL(d0) + 10 * n * log10(d / d0) + X_sigma
            RSSI(d) = P_tx - PL(d)

        where:
        - d = distance in meters
        - n = path_loss_exponent (typically 2.5 - 3.5 indoors)
        - X_sigma = Gaussian shadow fading ~ N(0, shadow_fading_std^2)
        - RSSI is clamped between -95.0 dBm (noise floor) and -30.0 dBm (antenna saturation).
        """
        dist = self.distance_to(client_x, client_y)
        
        # Log-distance path loss
        path_loss = self.reference_loss_1m + 10.0 * self.path_loss_exponent * math.log10(dist)
        
        # Add shadow fading (random Gaussian variation simulating multipath/obstacles)
        if rng is not None:
            fading = rng.gauss(0.0, shadow_fading_std)
        else:
            fading = random.gauss(0.0, shadow_fading_std)

        raw_rssi = self.tx_power_dbm - (path_loss + fading)
        
        # Realistic Wi-Fi receiver sensitivity limits:
        # -30 dBm is very close to antenna; -95 dBm is the threshold of disconnection
        clamped_rssi = max(-95.0, min(-30.0, raw_rssi))
        return round(clamped_rssi, 2)

    def calculate_qos(
        self,
        rssi: float,
        rng: Optional[random.Random] = None
    ) -> Tuple[float, float]:
        """
        Calculates Latency (ms) and Packet Loss Rate (0.0 to 1.0) based on:
        1. Current RSSI (weak signals force lower Modulation and Coding Scheme, causing retransmissions)
        2. Channel congestion (load_factor causes queueing delay and collisions)
        
        Returns:
            Tuple[float, float]: (latency_ms, packet_loss_rate)
        """
        # 1. Signal quality factor (0.0 = terrible at -95 dBm, 1.0 = perfect at >= -50 dBm)
        signal_factor = max(0.0, min(1.0, (rssi - (-95.0)) / 45.0))
        
        # 2. Latency calculation:
        # Base latency + Congestion queuing delay + Signal degradation delay + random jitter
        jitter = (rng.uniform(-2.0, 3.0) if rng else random.uniform(-2.0, 3.0))
        congestion_latency = self.load_factor * 45.0  # up to +45ms if channel is saturated
        weak_signal_latency = (1.0 - signal_factor) * 35.0 # up to +35ms due to MCS backoff
        latency = max(4.0, self.base_latency_ms + congestion_latency + weak_signal_latency + jitter)

        # 3. Packet loss calculation:
        # Base loss + Collision loss from load + Bit error rate from weak signal
        load_loss = (self.load_factor ** 2) * 0.12 # up to 12% loss under heavy contention
        signal_loss = ((1.0 - signal_factor) ** 2) * 0.25 # up to 25% loss when signal is near cutoff
        total_loss = min(0.95, self.base_packet_loss + load_loss + signal_loss)

        return round(latency, 2), round(total_loss, 4)

    def measure(
        self,
        client_x: float,
        client_y: float,
        shadow_fading_std: float = 1.5,
        rng: Optional[random.Random] = None
    ) -> Dict[str, Any]:
        """
        Simulates an active beacon probe or measurement scan from the mobile client.
        Returns a dictionary of current channel parameters.
        """
        dist = self.distance_to(client_x, client_y)
        rssi = self.calculate_rssi(client_x, client_y, shadow_fading_std=shadow_fading_std, rng=rng)
        latency_ms, packet_loss = self.calculate_qos(rssi, rng=rng)

        return {
            "ap_id": self.ap_id,
            "ssid": self.ssid,
            "channel": self.channel,
            "distance_m": round(dist, 2),
            "rssi_dbm": rssi,
            "load_factor": self.load_factor,
            "latency_ms": latency_ms,
            "packet_loss_rate": packet_loss,
            "pdr_pct": round((1.0 - packet_loss) * 100.0, 2)
        }
