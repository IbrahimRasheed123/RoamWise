# RoamWise — 20-Minute Project Presentation Plan

This presentation script is tailored for a third-year IT engineering seminar, project progress defense, or final viva evaluation.

---

## Presentation Timing Summary (20 Minutes Total)
- **Part 1: Motivation & Problem Formulation** (Slides 1–3) — 5 mins
- **Part 2: Technical Approach & Algorithm Design** (Slides 4–6) — 6 mins
- **Part 3: Live Demonstration & Results Analysis** (Slides 7–8) — 6 mins
- **Part 4: Conclusion, Future Scope & Q&A** (Slides 9–10) — 3 mins

---

## Slide-by-Slide Script & Talking Points

### Slide 1: Title & Introduction (1:00 min)
- **Title**: RoamWise — A Smart Wi-Fi Handoff Stability Simulator
- **Presenter**: [Your Name], 3rd Year B.Tech / B.E. Information Technology
- **Opening Statement**:
  > "Good morning, respected professors and evaluation committee members. Today, I am presenting RoamWise, an interactive simulation platform that studies and solves connection instability and ping-pong flapping in mobile Wi-Fi networks."

---

### Slide 2: Problem Statement & Wi-Fi Mobility (2:00 mins)
- **Core Concept**:
  - In modern enterprise networks (campuses, hospitals, warehouses), users are mobile.
  - A device must roam between multiple Access Points (APs) sharing a common SSID.
- **The Core Trade-off**:
  - Wi-Fi handoffs are "Break-before-Make" (hard handoff), causing an 80–150ms interruption.
  - Making handoffs too easily leads to **ping-pong oscillations**.
  - Making handoffs too difficult leads to **sticky client syndrome** and dead zones.

---

### Slide 3: The Ping-Pong Effect & TCP Degradation (2:00 mins)
- **Visual**: Diagram showing client flapping between AP-1 and AP-2 in the overlap zone.
- **Talking Points**:
  - In boundary regions, multipath reflections cause signals to flutter by $\pm 2$ to $4\text{ dBm}$.
  - A greedy RSSI-only approach switches back and forth continuously.
  - Each flap incurs disassociation, probe scanning, and reassociation overhead.
  - Packets are dropped during the transition, causing TCP sender congestion window (`cwnd`) collapse and video streaming buffering.

---

### Slide 4: Related Standards & Academic Background (2:00 mins)
- **Standards**:
  - **IEEE 802.11r**: Fast BSS Transition (reduces key handshake delay).
  - **IEEE 802.11k**: Radio Resource Measurement (neighbor reports).
  - **IEEE 802.11v**: Wireless Network Management (BSS transition management).
- **Key Insight**:
  > "IEEE standards specify the signaling protocol, but they do NOT dictate the handoff decision algorithm. The client firmware decides when to jump. That is where RoamWise provides an optimized solution."

---

### Slide 5: System Architecture & Mathematical Foundations (3:00 mins)
- **Propagation Physics**:
  - Log-Distance Path Loss Model: $PL(d) = PL(d_0) + 10 n \log_{10}(d/d_0) + X_\sigma$.
  - Realistic Gaussian Shadow Fading: $X_\sigma \sim \mathcal{N}(0, \sigma^2)$.
- **Architecture Highlights**:
  - Modular Python architecture with strict separation between physics, algorithms, metrics, and visualization.
  - Deterministic random seeding ensures 100% fair and identical comparison traces.

---

### Slide 6: Handoff Strategies Compared (3:00 mins)
- **Strategy 1: Basic (Greedy RSSI)**:
  - Switches immediately if another AP has higher signal. Highly unstable.
- **Strategy 2: Persistence (Fixed Hysteresis)**:
  - Requires candidate to maintain $+3\text{ dBm}$ advantage for 3 consecutive steps. Reduces flapping, but static parameters lag during sudden signal dropouts and ignore congestion.
- **Strategy 3: RoamWise (Our Contribution)**:
  - **Adaptive Margin**: $\Delta_{\text{adaptive}} = \Delta_{\text{base}} + \alpha \cdot \sigma_{\text{RSSI}}$.
  - **Cross-Layer QoS**: Evaluates RSSI, Latency, Channel Load, and Packet Loss.
  - **Emergency Fast-Roam**: Instant failover if RSSI drops below $-82\text{ dBm}$.
  - **Anti-Ping-Pong Memory**: Prevents bouncing back to an AP deserted within 4 steps.

---

### Slide 7: Live Demonstration (4:00 mins)
- **Demonstration Steps**:
  1. Open Streamlit dashboard at `http://localhost:8501`.
  2. Select **Scenario 2 (Fluctuating Signals / Ping-Pong Alley)**:
     - Show how Basic RSSI causes 15+ handoffs and multiple ping-pong flaps.
     - Show how RoamWise widens its adaptive margin ($\sigma \approx 3.4\text{ dB}$) and eliminates unnecessary handoffs.
  3. Select **Scenario 4 (Congested Hotspot)**:
     - Show that Basic and Persistence stay trapped on AP-1 because of raw signal.
     - Show how RoamWise roams to AP-2 because of lower latency and zero packet loss.
  4. Demonstrate CSV data export.

---

### Slide 8: Quantitative Results (2:00 mins)
- **Metrics Comparison Table**:
  - Handoff Reduction: **>70% decrease in total handoffs**.
  - Ping-Pong Elimination: **Up to 100% reduction in flapping**.
  - Packet Delivery Ratio (PDR): **Improved from ~82% to >96%**.
  - Average Latency: **Reduced by 30–45% in congested/obstacle scenarios**.
  - Quality of Experience (QoE): **MOS score increased from 2.6 to 4.5+**.

---

### Slide 9: Assumptions, Limitations & Future Scope (1:00 min)
- **Assumptions**: 2D floor plan, 1-second discrete time steps, hard handoff model.
- **Future Scope**:
  - Machine learning (Reinforcement Learning / Q-Learning) for predictive handoffs.
  - 3D indoor obstacle ray-tracing.
  - Physical integration on OpenWrt / Linux Raspberry Pi access points.

---

### Slide 10: Conclusion & Acknowledgments (1:00 min)
- **Closing Statement**:
  > "In conclusion, RoamWise demonstrates that Wi-Fi handoff stability can be dramatically improved without expensive hardware upgrades simply by using statistical signal variance and cross-layer intelligence. Thank you, and I am now ready for your questions."
