# RoamWise — Academic Project Report Outline

This outline follows the standard B.Tech / B.E. Information Technology academic project report formatting requirements.

---

## Preliminary Pages
1. **Title Page**: RoamWise — A Smart Wi-Fi Handoff Stability Simulator
2. **Certificate of Approval**: Signed by Internal Guide, Head of Department (HOD), and External Examiner.
3. **Student Declaration**: Originality declaration stating work was completed by the candidate.
4. **Acknowledgments**: Thanks to faculty mentor, department lab staff, and institution.
5. **Abstract**:
   - Background of IEEE 802.11 wireless mobility and hard handoff latency.
   - The challenge of ping-pong flapping in boundary zones and sticky client degradation.
   - Proposed RoamWise methodology combining adaptive variance-based hysteresis and cross-layer quality scoring.
   - Summary of empirical simulation results (elimination of ping-pong handoffs, 96%+ PDR).
6. **Keywords**: Wi-Fi Roaming, IEEE 802.11, Handoff Stability, Ping-Pong Effect, Adaptive Hysteresis, Cross-Layer QoS.
7. **Table of Contents, List of Figures, List of Tables, List of Abbreviations**.

---

## Chapter 1: Introduction
- **1.1 Background & Motivation**: Rise of mobile wireless devices (smartphones, IoT, AGVs, laptops) in enterprise environments.
- **1.2 Wi-Fi Roaming Fundamentals**: Transitioning between BSSIDs within a single ESSID; Break-Before-Make hard handoff characteristics.
- **1.3 Problem Statement**: Detailing the ping-pong flapping phenomenon caused by multipath fading and the failure of greedy RSSI algorithms.
- **1.4 Project Objectives**:
  - Implement realistic Log-Distance Path Loss and Gaussian shadow fading propagation models.
  - Implement and benchmark Basic (Greedy), Persistence (Fixed Hysteresis), and RoamWise (Adaptive) strategies.
  - Design an interactive, reproducible Streamlit dashboard for real-time visualization and faculty demonstration.
  - Provide an automated test suite verifying mathematical consistency and determinism.
- **1.5 Report Organization**: Summary of subsequent chapters.

---

## Chapter 2: Literature Review & Related Work
- **2.1 Overview of IEEE 802.11 Roaming Standards**:
  - IEEE 802.11k (Radio Resource Measurement & Neighbor Reports).
  - IEEE 802.11v (Wireless Network Management & BSS Transition Management).
  - IEEE 802.11r (Fast Basic Service Set Transition / Fast Roaming).
- **2.2 Existing Handoff Decision Techniques**:
  - RSSI Threshold & Hysteresis Algorithms (Cellular and early WLAN).
  - Time-To-Trigger (TTT) and Dwell-Time mechanisms.
  - Fuzzy Logic and Multi-Criteria Decision Making (MCDM) approaches.
- **2.3 Research Gaps Identified**:
  - Static hysteresis fails to adapt to dynamic radio turbulence.
  - Pure physical-layer metrics ignore channel load and queueing latency.
  - Need for an accessible, reproducible educational simulator.

---

## Chapter 3: Wireless Channel & Physical System Modeling
- **3.1 Access Point System Model**: Transmit power ($P_{\text{tx}}$), coordinates, operating channel, channel load factor.
- **3.2 Log-Distance Path Loss Formulation**:
  $$PL(d) = PL(d_0) + 10 \cdot n \cdot \log_{10}(d/d_0) + X_\sigma$$
- **3.3 Shadow Fading Modeling**: Zero-mean Gaussian random variable $X_\sigma \sim \mathcal{N}(0, \sigma^2)$.
- **3.4 Modulation & Coding Scheme (MCS) Quality Derivation**: Mathematical mapping between RSSI, load, latency, and packet loss.
- **3.5 Handoff Interruption Delay Model**: Break-before-make transition penalty (100 ms default).

---

## Chapter 4: Proposed RoamWise Methodology
- **4.1 Architecture of RoamWise Decision Engine**:
- **4.2 Real-Time Statistical Variance Estimation**:
  - Sliding window buffer of length $W = 5$.
  - Sample standard deviation ($\sigma_{\text{RSSI}}$) calculation.
- **4.3 Dynamic Adaptive Hysteresis Margin**:
  $$\Delta_{\text{adaptive}} = \Delta_{\text{base}} + \alpha \cdot \sigma_{\text{RSSI}}$$
- **4.4 Cross-Layer Composite Quality Score ($Q_{\text{AP}}$)**:
  - Multi-attribute utility formulation combining RSSI, Latency, Channel Load, and Packet Loss.
- **4.5 Emergency Fast-Roam Failover**:
  - Trigger conditions (RSSI $< -82\text{ dBm}$ or Loss $> 22\%$).
  - Instantaneous association failover bypassing dwell time.
- **4.6 Anti-Ping-Pong Cooldown Memory**:
  - Historical AP blacklist buffer and dampening margin.

---

## Chapter 5: System Implementation & Software Design
- **5.1 Modular Architecture**:
  - `access_point.py`, `handoff_algorithms.py`, `scenarios.py`, `simulator.py`, `metrics.py`, `app.py`.
- **5.2 Simulation Trace Determinism**:
  - Seed-controlled channel trace precomputation for fair benchmarking.
- **5.3 Streamlit Interactive Dashboard Design**:
  - Custom UI design, responsive layout, sidebar control system.
- **5.4 Interactive Plotly Visualizations**:
  - Multi-line signal trajectories, 2D physical floor map, performance radar and bar charts.
- **5.5 Automated Testing Suite**:
  - Python `unittest` test cases covering signal physics, algorithm transitions, metric accuracy, and scenario consistency.

---

## Chapter 6: Experimental Results & Comparative Evaluation
- **6.1 Benchmark Scenarios**:
  - Scenario 1: Stable Linear Walk.
  - Scenario 2: Fluctuating Signals (Ping-Pong Alley).
  - Scenario 3: Deteriorating Connection (Sudden Wall Obstacle).
  - Scenario 4: Congested Hotspot (High Load vs Clean AP).
- **6.2 Performance Metrics Evaluated**:
  - Total Handoff Count, Ping-Pong Handoff Count, Packet Delivery Ratio (PDR %), Average & P95 Latency (ms), Total Interruption Time (ms), QoE MOS.
- **6.3 Quantitative Findings & Discussion**:
  - Ping-Pong reduction: basic flapped 15+ times; RoamWise reduced flapping to 0.
  - PDR improvement: from ~82% in basic to >96% in RoamWise.
  - Cross-layer resilience: successful avoidance of saturated APs.

---

## Chapter 7: Conclusion & Future Scope
- **7.1 Conclusion**: Summary of project outcomes and engineering contributions.
- **7.2 Limitations**: 2D geometric assumption, 1-second discrete time steps, single-antenna model.
- **7.3 Future Enhancements**:
  - Machine learning (Reinforcement Learning / Deep Q-Networks) for predictive trajectory forecasting.
  - Physical testbed validation using Raspberry Pi 4 nodes and OpenWrt routers.
  - Integration with 802.11be (Wi-Fi 7) Multi-Link Operation (MLO).

---

## References (Sample IEEE Format)
1. IEEE Std 802.11-2020, "Wireless LAN Medium Access Control (MAC) and Physical Layer (PHY) Specifications," IEEE, 2020.
2. T. S. Rappaport, *Wireless Communications: Principles and Practice*, 2nd ed., Prentice Hall, 2002.
3. IEEE Std 802.11r-2008, "Fast Basic Service Set (BSS) Transition," IEEE Computer Society, 2008.
4. IEEE Std 802.11k-2008, "Radio Resource Measurement of Wireless LANs," IEEE Computer Society, 2008.
5. IEEE Std 802.11v-2011, "Wireless Network Management," IEEE Computer Society, 2011.
