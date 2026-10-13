"""
RoamWise — Simulation Scenarios Generator
-----------------------------------------
This module provides realistic, reproducible mobility and wireless scenarios:
1. Stable Linear Walk (Baseline transition across 3 APs)
2. Fluctuating Boundary (Heavy multipath fading causing ping-pong oscillation)
3. Deteriorating Connection (Sudden shadowing / elevator obstacle requiring fast roam)
4. Congested Hotspot (Strong signal but saturated channel load vs idle AP)
5. Custom Dynamic Scenario (User-configured parameters)

All scenarios support a reproducible random seed for deterministic evaluation.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Callable
import random
from access_point import AccessPoint


@dataclass
class Scenario:
    """
    Encapsulates a full simulation scenario run definition.
    """
    scenario_id: str
    title: str
    description: str
    duration_steps: int
    access_points: List[AccessPoint]
    trajectory: List[Tuple[float, float]] # Client (x, y) coordinates at each time step
    shadow_fading_std: float              # Environmental noise level (dB)
    initial_ap_id: str = "AP-1"
    step_events: Optional[Dict[int, Any]] = None


def create_stable_linear_walk(seed: int = 42) -> Scenario:
    """
    Scenario 1: Stable Linear Walk.
    A mobile user walks smoothly through an office hallway from (5, 20) to (95, 20).
    Three APs are placed at x=15m, x=50m, and x=85m.
    Environment has low shadow fading (0.8 dB).
    """
    aps = [
        AccessPoint(ap_id="AP-1", ssid="RoamWise-Mesh", channel=1, frequency_ghz=2.4, tx_power_dbm=20.0, x=15.0, y=20.0, load_factor=0.20, base_latency_ms=8.0),
        AccessPoint(ap_id="AP-2", ssid="RoamWise-Mesh", channel=6, frequency_ghz=2.4, tx_power_dbm=20.0, x=50.0, y=20.0, load_factor=0.25, base_latency_ms=9.0),
        AccessPoint(ap_id="AP-3", ssid="RoamWise-Mesh", channel=11, frequency_ghz=2.4, tx_power_dbm=20.0, x=85.0, y=20.0, load_factor=0.20, base_latency_ms=8.0),
    ]

    duration = 90
    trajectory = []
    start_x, end_x = 5.0, 95.0
    for step in range(duration):
        progress = step / (duration - 1)
        curr_x = start_x + progress * (end_x - start_x)
        curr_y = 20.0
        trajectory.append((round(curr_x, 2), round(curr_y, 2)))

    return Scenario(
        scenario_id="stable_linear_walk",
        title="1. Stable Linear Walk (Corridor Transition)",
        description="Mobile client walks in a straight line past 3 APs in a low-noise environment. Demonstrates normal planned roaming transitions.",
        duration_steps=duration,
        access_points=aps,
        trajectory=trajectory,
        shadow_fading_std=0.8,
        initial_ap_id="AP-1"
    )


def create_fluctuating_boundary(seed: int = 42) -> Scenario:
    """
    Scenario 2: Fluctuating Signals (Ping-Pong Alley).
    The mobile client lingers around the boundary zone (x ≈ 32m) between AP-1 (15m) and AP-2 (50m).
    High shadow fading (3.4 dB) creates intense signal fluctuation.
    Naive greedy switching causes continuous ping-pong handoffs.
    """
    aps = [
        AccessPoint(ap_id="AP-1", ssid="RoamWise-Mesh", channel=1, frequency_ghz=2.4, tx_power_dbm=20.0, x=15.0, y=20.0, load_factor=0.25, base_latency_ms=8.0),
        AccessPoint(ap_id="AP-2", ssid="RoamWise-Mesh", channel=6, frequency_ghz=2.4, tx_power_dbm=20.0, x=50.0, y=20.0, load_factor=0.25, base_latency_ms=8.0),
        AccessPoint(ap_id="AP-3", ssid="RoamWise-Mesh", channel=11, frequency_ghz=2.4, tx_power_dbm=20.0, x=85.0, y=20.0, load_factor=0.20, base_latency_ms=8.0),
    ]

    duration = 75
    trajectory = []
    # Client hovers around x=31m to 34m with slight wandering
    rng = random.Random(seed)
    base_x = 32.5
    for step in range(duration):
        jitter = rng.uniform(-1.5, 1.5)
        curr_x = base_x + jitter
        curr_y = 20.0 + rng.uniform(-0.5, 0.5)
        trajectory.append((round(curr_x, 2), round(curr_y, 2)))

    return Scenario(
        scenario_id="fluctuating_boundary",
        title="2. Fluctuating Signals (Ping-Pong Alley)",
        description="Mobile client hovers near the overlap boundary between AP-1 and AP-2 under heavy shadow fading (σ=3.4 dB). Exposes ping-pong flapping in naive algorithms.",
        duration_steps=duration,
        access_points=aps,
        trajectory=trajectory,
        shadow_fading_std=3.4,
        initial_ap_id="AP-1"
    )


def create_deteriorating_connection(seed: int = 42) -> Scenario:
    """
    Scenario 3: Deteriorating Connection (Sudden Shadowing / Wall Obstacle).
    Client is near AP-1, but moves behind a thick concrete structural column/elevator at step 28.
    AP-1's signal suddenly drops sharply by 20 dB, risking an immediate connection drop.
    RoamWise detects critical signal/packet loss and triggers Emergency Fast-Roam.
    """
    aps = [
        AccessPoint(ap_id="AP-1", ssid="RoamWise-Mesh", channel=1, frequency_ghz=2.4, tx_power_dbm=20.0, x=15.0, y=20.0, load_factor=0.20, base_latency_ms=8.0),
        AccessPoint(ap_id="AP-2", ssid="RoamWise-Mesh", channel=6, frequency_ghz=2.4, tx_power_dbm=20.0, x=45.0, y=20.0, load_factor=0.20, base_latency_ms=9.0),
        AccessPoint(ap_id="AP-3", ssid="RoamWise-Mesh", channel=11, frequency_ghz=2.4, tx_power_dbm=20.0, x=80.0, y=20.0, load_factor=0.15, base_latency_ms=8.0),
    ]

    duration = 70
    trajectory = []
    # Client moves from (18, 20) towards (42, 20)
    for step in range(duration):
        progress = step / (duration - 1)
        curr_x = 18.0 + progress * 24.0
        curr_y = 20.0
        trajectory.append((round(curr_x, 2), round(curr_y, 2)))

    # Dynamic step event: at step 28, a reinforced concrete obstacle column causes a 32 dB attenuation plunge
    # Using pure dictionary so it is 100% serializable by Streamlit cache (@st.cache_data)
    step_events = {
        28: [
            {
                "ap_id": "AP-1",
                "tx_power_dbm": -12.0, # Attenuation drop pushing AP-1 RSSI below -82 dBm cutoff
                "load_factor": 0.50
            }
        ]
    }

    return Scenario(
        scenario_id="deteriorating_connection",
        title="3. Deteriorating Connection (Sudden Obstacle / Dead Zone)",
        description="At step 28, a thick architectural barrier obstructs AP-1, causing a severe attenuation plunge. Tests how fast algorithms rescue the connection.",
        duration_steps=duration,
        access_points=aps,
        trajectory=trajectory,
        shadow_fading_std=1.2,
        initial_ap_id="AP-1",
        step_events=step_events
    )


def create_congested_hotspot(seed: int = 42) -> Scenario:
    """
    Scenario 4: Congested Hotspot (Cross-Layer Roaming).
    Client is physically close to AP-1 (strong RSSI ~ -55 dBm), but AP-1 is severely congested
    (88% channel load, high latency, 15% packet loss).
    AP-2 is slightly further away (RSSI ~ -68 dBm), but completely idle (15% load, 9ms latency).
    Greedy and Persistence strategies stay stuck on AP-1 because of pure RSSI.
    RoamWise detects the poor QoS and roams to the healthy AP-2.
    """
    aps = [
        AccessPoint(ap_id="AP-1", ssid="RoamWise-Mesh", channel=1, frequency_ghz=2.4, tx_power_dbm=20.0, x=20.0, y=20.0, load_factor=0.88, base_latency_ms=35.0, base_packet_loss=0.08),
        AccessPoint(ap_id="AP-2", ssid="RoamWise-Mesh", channel=6, frequency_ghz=2.4, tx_power_dbm=20.0, x=55.0, y=20.0, load_factor=0.15, base_latency_ms=8.0, base_packet_loss=0.003),
        AccessPoint(ap_id="AP-3", ssid="RoamWise-Mesh", channel=11, frequency_ghz=2.4, tx_power_dbm=20.0, x=85.0, y=20.0, load_factor=0.20, base_latency_ms=9.0, base_packet_loss=0.005),
    ]

    duration = 60
    trajectory = []
    # Client sits comfortably at x=28m (closer to AP-1 than AP-2)
    for step in range(duration):
        trajectory.append((28.0, 20.0))

    return Scenario(
        scenario_id="congested_hotspot",
        title="4. Congested Hotspot (Cross-Layer QoS Evaluation)",
        description="AP-1 has strong signal but is 88% congested with high packet loss. AP-2 has slightly lower signal but clean airtime. Tests cross-layer intelligence.",
        duration_steps=duration,
        access_points=aps,
        trajectory=trajectory,
        shadow_fading_std=1.0,
        initial_ap_id="AP-1"
    )


def create_custom_scenario(
    duration_steps: int = 80,
    client_speed_mps: float = 1.0,
    shadow_fading_std: float = 2.0,
    ap1_load: float = 0.20,
    ap2_load: float = 0.30,
    ap3_load: float = 0.20,
    seed: int = 42
) -> Scenario:
    """
    Dynamic scenario generator allowing user adjustment of environment parameters.
    """
    aps = [
        AccessPoint(ap_id="AP-1", ssid="RoamWise-Mesh", channel=1, frequency_ghz=2.4, tx_power_dbm=20.0, x=15.0, y=20.0, load_factor=ap1_load, base_latency_ms=8.0),
        AccessPoint(ap_id="AP-2", ssid="RoamWise-Mesh", channel=6, frequency_ghz=2.4, tx_power_dbm=20.0, x=50.0, y=20.0, load_factor=ap2_load, base_latency_ms=9.0),
        AccessPoint(ap_id="AP-3", ssid="RoamWise-Mesh", channel=11, frequency_ghz=2.4, tx_power_dbm=20.0, x=85.0, y=20.0, load_factor=ap3_load, base_latency_ms=8.0),
    ]

    trajectory = []
    start_x = 10.0
    for step in range(duration_steps):
        curr_x = min(90.0, start_x + (step * client_speed_mps * 1.0))
        trajectory.append((round(curr_x, 2), 20.0))

    return Scenario(
        scenario_id="custom_scenario",
        title="5. Custom User Scenario",
        description=f"User-customized simulation: Duration={duration_steps}s, Speed={client_speed_mps}m/s, Noise σ={shadow_fading_std}dB.",
        duration_steps=duration_steps,
        access_points=aps,
        trajectory=trajectory,
        shadow_fading_std=shadow_fading_std,
        initial_ap_id="AP-1"
    )


def get_all_scenarios(seed: int = 42) -> Dict[str, Scenario]:
    """Returns a dictionary mapping scenario keys to initialized Scenario instances."""
    return {
        "stable_linear_walk": create_stable_linear_walk(seed=seed),
        "fluctuating_boundary": create_fluctuating_boundary(seed=seed),
        "deteriorating_connection": create_deteriorating_connection(seed=seed),
        "congested_hotspot": create_congested_hotspot(seed=seed)
    }
