# RoamWise — Comprehensive Faculty Viva & Exam Preparation Guide

This guide prepares you to explain and defend **RoamWise** during your third-year IT engineering project evaluation, lab viva, and semester presentations.

---

## Part 1: Core Computer Networks & Wireless Foundations

### Q1. What is Wi-Fi Roaming (Handoff)?
**Answer:**
Wi-Fi roaming is the process where a mobile client station (STA) transitions its wireless association from one Access Point (AP) to another Access Point within the same Extended Service Set (ESS / common SSID) without losing its IP address or terminating active transport-layer sessions (e.g., TCP connections or UDP streams).

### Q2. What is the difference between BSSID and ESSID?
**Answer:**
- **BSSID (Basic Service Set Identifier)**: The unique 48-bit MAC address of the specific radio interface of an Access Point (e.g., `00:14:22:01:23:45`).
- **ESSID (Extended Service Set Identifier)**: The human-readable network name broadcast to users (e.g., `RoamWise-Mesh` or `Campus-WiFi`). Multiple APs share the same ESSID to provide roaming coverage across a building.

### Q3. What is RSSI, and why is it expressed in negative numbers?
**Answer:**
**RSSI (Received Signal Strength Indicator)** is the measured power of the received radio signal at the client antenna.
- It is expressed in **dBm** (decibels relative to 1 milliwatt):
  $$P_{\text{dBm}} = 10 \cdot \log_{10}\left(\frac{P_{\text{mW}}}{1\text{ mW}}\right)$$
- Because received wireless signals are tiny fractions of a milliwatt (e.g., $10^{-6}\text{ mW}$ to $10^{-3}\text{ mW}$), the logarithm is negative:
  - $-30\text{ dBm}$ = Exceptionally strong signal (client is right next to the AP).
  - $-67\text{ dBm}$ = Recommended minimum signal for VoIP and streaming.
  - $-80\text{ dBm}$ = Weak signal; frequent retransmissions.
  - $-95\text{ dBm}$ = Noise floor; cutoff threshold where connection drops.

### Q4. What is the difference between RSSI and SNR?
**Answer:**
- **RSSI** measures the total received power (signal + background noise + interference).
- **SNR (Signal-to-Noise Ratio)** measures the ratio of the true signal power to the background noise floor power ($\text{SNR} = \text{RSSI} - \text{NoiseFloor}$). High SNR means clean, decipherable data symbols.

### Q5. What frames are exchanged during a standard 802.11 roaming handoff?
**Answer:**
1. **Probe Request / Probe Response** (Active Scanning) OR **Beacon Listening** (Passive Scanning).
2. **Open System Authentication Request & Response** with the new AP.
3. **Reassociation Request & Response** with the new AP (containing the BSSID of the old AP).
4. **4-Way Handshake** (in WPA2/WPA3 networks to derive fresh encryption keys).
5. **Bridge Update / IAPP (802.11f)**: The new AP sends an Ethernet frame to the distribution switch so switches update their MAC address forwarding tables.

### Q6. Why does a standard handoff cause packet loss and delay?
**Answer:**
Standard IEEE 802.11 uses a **Break-Before-Make** (hard handoff) architecture. The client radio has a single transceiver, so it must disassociate from channel $A$ and tune its radio synthesizer to channel $B$ to authenticate. This process typically takes **80 ms to 150 ms**. Packets in flight during this transition are discarded, causing TCP retransmissions.

---

## Part 2: The Ping-Pong Problem & Switching Strategies

### Q7. What is the "Ping-Pong Effect"?
**Answer:**
The **Ping-Pong Effect** (or handoff oscillation) is the rapid, repeated switching of a client between two adjacent Access Points ($AP_1 \rightarrow AP_2 \rightarrow AP_1 \rightarrow AP_2$) over a short duration.

### Q8. Why does the Ping-Pong Effect occur?
**Answer:**
In boundary zones between two APs, signal strength naturally fluctuates due to:
- **Multipath Fading** (constructive and destructive radio wave interference).
- **Shadow Fading** (moving people, doors opening, physical obstacles).
A naive greedy algorithm switches the moment another AP measures $0.1\text{ dBm}$ higher. Small variations cause constant back-and-forth flapping.

### Q9. Why is the Ping-Pong Effect so harmful to network performance?
**Answer:**
1. **Throughput Collapse**: Every switch causes an 80–150ms blackhole. Packet drops cause TCP to enter Slow Start or Fast Recovery, slashing the congestion window (`cwnd`).
2. **Channel Airtime Waste**: Heavy flood of management frames (probes, authentications, associations) degrades the channel for all nearby users.
3. **Battery Drain**: Frequent scanning and frame handshakes drain mobile device batteries.

### Q10. What is Hysteresis in networking?
**Answer:**
Hysteresis is a mechanism where state transitions depend not only on the current input value, but also on past state and an additional offset threshold ($\Delta$). In Wi-Fi handoffs:
$$\text{RSSI}_{\text{candidate}} > \text{RSSI}_{\text{current}} + \Delta_{\text{hyst}}$$
A candidate must be better by a distinct margin before a switch is considered.

### Q11. What is the limitation of Fixed-Hysteresis Persistence switching?
**Answer:**
- It uses static, hardcoded numbers (e.g. $+3\text{ dBm}$ margin and $3$ steps dwell time).
- In noisy environments ($\sigma > 3.5\text{ dB}$), $3\text{ dBm}$ is too narrow and still flutters.
- In sudden signal drop-offs (entering an elevator or behind a concrete wall), waiting for 3 dwell steps causes complete connection drop before the handoff completes.
- It is **blind to network congestion** (an AP with strong RSSI could be 95% congested).

---

## Part 3: RoamWise Architecture & Innovation

### Q12. What are the key innovations in RoamWise?
**Answer:**
1. **Adaptive Hysteresis via Moving Standard Deviation**:
   $$\Delta_{\text{adaptive}} = \Delta_{\text{base}} + \alpha \cdot \sigma_{\text{RSSI}}$$
   Instead of a static margin, RoamWise dynamically widens the threshold when channel variance is high and relaxes it when the channel is calm.
2. **Cross-Layer Composite Quality Score ($Q_{\text{AP}}$)**:
   Evaluates physical signal (RSSI), latency, channel congestion, and packet loss rate.
3. **Emergency Fast-Roam Failover**:
   Bypasses dwell persistence if current connection drops below $-82\text{ dBm}$ or packet loss exceeds $22\%$.
4. **Anti-Ping-Pong Memory**:
   Applies a temporary cooldown margin if attempting to switch back to a recently deserted AP.

### Q13. How does RoamWise calculate the running standard deviation?
**Answer:**
It maintains a sliding window of the last $W$ measurements (default $W=5$ steps) using a Python `collections.deque(maxlen=5)`. It computes the sample standard deviation $\sigma = \sqrt{\frac{1}{W-1}\sum (x_i - \mu)^2}$. This provides an $O(1)$ amortized memory footprint.

### Q14. What is Cross-Layer Design, and why is it used in RoamWise?
**Answer:**
In the classical OSI model, layers are strictly isolated. However, Physical layer RSSI alone does not reflect application performance: an AP can have strong signal ($-55\text{ dBm}$) but be saturated by 60 active downloading clients (high MAC channel load).
RoamWise reads Physical (RSSI), MAC (channel load / BSS load), and Transport/Network (latency, loss) indicators to compute a holistic Quality Score.

### Q15. How does RoamWise relate to IEEE 802.11k, 802.11v, and 802.11r?
**Answer:**
- **IEEE 802.11k**: Radio Resource Measurement (neighbor reports).
- **IEEE 802.11v**: BSS Transition Management (network assists client with load data).
- **IEEE 802.11r**: Fast BSS Transition (reduces handoff latency to $<50\text{ ms}$).
- **RoamWise's Role**: The IEEE standards define the **communication protocol and frame syntax**, but **the decision algorithm** is deliberately left unspecified by the IEEE standard. Vendors implement proprietary roaming algorithms. RoamWise is an intelligent client-side decision algorithm compatible with 802.11k/v telemetry.

---

## Part 4: Simulation Methodology & Technical Defense

### Q16. Why did you use a simulation instead of physical Wi-Fi routers?
**Answer:**
1. **Reproducibility**: In physical air, radio signals cannot be frozen or replicated. Two tests run 5 minutes apart experience different RF interference. In simulation, using a **random seed** ensures all three algorithms face the **exact same channel trace**.
2. **Controlled Parameter Sweeps**: Simulation allows testing extreme conditions (sudden 20 dB shadowing, 88% channel saturation, multipath noise $\sigma = 3.5\text{ dB}$) safely and without enterprise hardware cost.
3. **Scientific Benchmarking**: Standard academic networking research (e.g., NS-3, OMNeT++) relies on mathematical simulation to isolate algorithmic differences from hardware quirks.

### Q17. What path loss model is implemented in `access_point.py`?
**Answer:**
The **Log-Distance Path Loss Model with Shadow Fading**:
$$PL(d) = PL(d_0) + 10 \cdot n \cdot \log_{10}(d / d_0) + X_\sigma$$
With $d_0 = 1\text{ m}$, $PL(d_0) = 40\text{ dB}$ (2.4 GHz reference), $n = 2.8$ (indoor office path loss exponent), and $X_\sigma \sim \mathcal{N}(0, \sigma^2)$ representing Gaussian shadow fading.

### Q18. How is packet delivery ratio (PDR) calculated?
**Answer:**
$$\text{PDR} = \left(1.0 - \text{MeanLossRate} - \text{HandoffLossPenalty}\right) \times 100\%$$
Where each handoff incurs a transient disruption penalty representing frames lost during the unmanaged authentication/association gap.

### Q19. How do you detect and count Ping-Pong handoffs?
**Answer:**
In `metrics.py`, we inspect the handoff event sequence. If a handoff from $AP_B \rightarrow AP_A$ occurs at step $t$, and a reciprocal transition $AP_A \rightarrow AP_B$ occurred at step $t - \Delta t$ where $\Delta t \le 5\text{ seconds}$, the event is flagged as a Ping-Pong handoff.

### Q20. What is the time complexity of RoamWise?
**Answer:**
- Scanning $N$ visible APs takes $O(N)$ time.
- Updating the sliding window of size $W$ takes $O(1)$ amortized time.
- Computing sample standard deviation takes $O(W)$ time.
- Total complexity per step is $O(N + W)$. Since $N \le 16$ and $W = 5$, execution takes **microseconds**, making it lightweight for real-time mobile microcontrollers.

---

## Part 5: Faculty "Trap" Questions & How to Answer Them

### Trap 1: "Is your RoamWise algorithm patented or did you invent handoffs?"
**Correct Response:**
> "No, sir/ma'am. The concepts of hysteresis and dwell time have been studied in cellular (GSM/LTE) and IEEE 802.11 standards. Our project contribution is the **adaptive synthesis**: dynamically scaling the hysteresis threshold using real-time moving standard deviation ($\sigma_{\text{RSSI}}$) paired with cross-layer QoS metrics and an emergency failover trigger, implemented in a clean, reproducible simulation testbed."

### Trap 2: "Why didn't you just set a huge hysteresis margin like 15 dBm to stop ping-pong?"
**Correct Response:**
> "A 15 dBm margin would indeed eliminate ping-pong, but it creates the **'Sticky Client' problem**. The device clings to an increasingly weak AP even when a much better AP is available, causing high latency, packet loss, and eventual connection dropouts. RoamWise adapts the margin dynamically so it is wide only when noise requires it, and tight when smooth transitions are needed."




### Trap 3: "Are your simulation results hardcoded?"
**Correct Response:**
> "Not at all, sir/ma'am. Every measurement is dynamically calculated at runtime based on the client's $(x, y)$ Euclidean coordinates, the Log-Distance path loss equation, and Gaussian noise generated with a seed. You can change the seed, adjust the client velocity, or modify noise standard deviation in the Streamlit sidebar, and the simulation recalculates in real-time."
