# RoamWise System Architecture

## 1. High-Level Overview
**RoamWise** is an IEEE 802.11 Wi-Fi handoff stability simulation platform. It models access points, radio wave propagation, client mobility, and handoff decision algorithms to evaluate connection stability and Quality of Experience (QoE).

The architecture is built on a clean **modular pipeline**:
1. **Physical & Wireless Environment Layer** (`access_point.py`): Models radio propagation, log-distance path loss, shadow fading, and channel congestion.
2. **Mobility & Scenario Generator** (`scenarios.py`): Defines 2D floor plans, AP deployments, client trajectory paths, and obstacle events.
3. **Roaming Decision Engine** (`handoff_algorithms.py`): Encapsulates the three switching strategies (Basic RSSI, Persistence Hysteresis, and RoamWise Adaptive Stability).
4. **Execution & Telemetry Engine** (`simulator.py`): Executes reproducible runs with a deterministic seed, providing identical channel traces to all algorithms.
5. **Analytics & Performance Engine** (`metrics.py`): Quantifies handoff count, ping-pong frequency, packet delivery ratio, latency, disruption time, and QoE MOS.
6. **Presentation & Interactive Layer** (`app.py`): A Streamlit web dashboard powered by Plotly for live visualization and CSV data export.

---

## 2. Component Architecture Diagram

```mermaid
graph TD
    subgraph UI_Layer ["Presentation Layer (Streamlit & Plotly)"]
        APP["app.py (Interactive Dashboard)"]
        VIZ["Plotly Visualizations (RSSI Curves, 2D Floor Map, Bar Charts)"]
        CSV_EXP["CSV Export Engine"]
    end

    subgraph Simulation_Core ["Simulation Engine"]
        SIM["simulator.py (Simulation Runner)"]
        TRACE["Deterministic Channel Trace Generator"]
    end

    subgraph Domain_Models ["Domain Models"]
        AP["access_point.py (AccessPoint Physics)"]
        SCEN["scenarios.py (Predefined & Custom Scenarios)"]
    end

    subgraph Decision_Engines ["Handoff Algorithms"]
        BASE_ALGO["BaseHandoffAlgorithm (Abstract Class)"]
        BASIC["BasicSignalHandoff (Greedy RSSI)"]
        PERS["PersistenceHandoff (Fixed Hysteresis + Dwell)"]
        ROAMWISE["RoamWiseHandoff (Adaptive StdDev + Multi-QoS)"]
    end

    subgraph Metrics_Layer ["Metrics & Analytics"]
        METRICS["metrics.py (KPI Engine)"]
        PP_DETECT["Ping-Pong Flapping Detector"]
        QOE_CALC["QoE MOS & Stability Calculator"]
    end

    APP --> SIM
    SIM --> SCEN
    SIM --> TRACE
    TRACE --> AP
    SIM --> Decision_Engines
    Decision_Engines -- inherits --> BASE_ALGO
    SIM --> METRICS
    METRICS --> PP_DETECT
    METRICS --> QOE_CALC
    SIM --> VIZ
    SIM --> CSV_EXP
```

---

## 3. Data Flow Pipeline

```mermaid
sequenceDiagram
    autonumber
    participant User as Student / Evaluator
    participant Dashboard as Streamlit (app.py)
    participant Sim as Simulator (simulator.py)
    participant AP as Access Points (access_point.py)
    participant Algo as Handoff Algorithm
    participant Metrics as Metrics Engine (metrics.py)

    User->>Dashboard: Select Scenario & Configure Parameters
    Dashboard->>Sim: run_comparison(scenario, algorithms)
    Note over Sim,AP: Step 1: Precompute Channel Trace (Deterministic Seed)
    loop For each time step t (0 to T-1)
        Sim->>AP: AP.measure(client_x, client_y, noise_sigma)
        AP-->>Sim: Measurements (RSSI, Latency, Loss, Load)
    end
    Note over Sim,Algo: Step 2: Evaluate All 3 Algorithms on Identical Trace
    loop For each Algorithm (Basic, Persistence, RoamWise)
        loop For each time step t
            Sim->>Algo: decide(current_ap, measurements, t)
            Algo-->>Sim: (target_ap, reason, telemetry)
        end
        Sim->>Metrics: calculate_metrics(telemetry, raw_handoffs)
        Metrics-->>Sim: SimulationMetricsSummary & Processed Events
    end
    Sim-->>Dashboard: Return Results Dictionary
    Dashboard->>User: Render Interactive Visualizations & Summary Cards
```

---

## 4. Module Responsibilities

| Module | Primary Class / Function | Responsibility |
| :--- | :--- | :--- |
| `access_point.py` | `AccessPoint` | Implements IEEE 802.11 Log-Distance path loss, shadow fading, load penalties, and QoS degradation calculations. |
| `handoff_algorithms.py` | `BaseHandoffAlgorithm`<br>`BasicSignalHandoff`<br>`PersistenceHandoff`<br>`RoamWiseHandoff` | Implements the decision-making rules for AP association and roaming transitions. |
| `scenarios.py` | `Scenario`, generator functions | Creates 4 standard scenarios (Linear Walk, Fluctuating Boundary, Obstacle, Congested Hotspot) and user-custom setups. |
| `simulator.py` | `Simulator`, `SimulationResult` | Runs algorithms against shared channel traces, ensuring fair scientific benchmarking. |
| `metrics.py` | `calculate_metrics()`, `HandoffEvent` | Detects ping-pong oscillations, computes PDR %, interruption latency, and composite QoE. |
| `app.py` | Streamlit Dashboard | User interface with scenario controls, parameter tuning, Plotly charts, 2D floor maps, and CSV exports. |
| `tests/` | `unittest` test suites | 18 automated unit tests covering mathematical accuracy, algorithm decision logic, and end-to-end simulation. |

---

## 5. Wireless Network Mapping (802.11 Concepts)

In physical IEEE 802.11 networks:
- **Station (STA)**: The mobile client (laptop, smartphone).
- **Access Point (AP)**: The wireless base station transmitting beacon frames every 100ms.
- **Probe Scanning**: The client scans channels (Active probe requests or passive beacon listening).
- **Hard Handoff ("Break-before-Make")**: The client must disassociate from the current AP before completing authentication and association with the new AP. This creates a disruption period of approximately 50ms–150ms.
- **RoamWise's Role**: RoamWise operates as the client's internal roaming decision policy, preventing bad handoff decisions that trigger packet drops.
