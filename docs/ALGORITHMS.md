# RoamWise Algorithm Specifications

This document outlines the mathematical models, decision rules, and complexity analysis for each strategy implemented in **RoamWise**.

---

## 1. Wireless Channel & Propagation Models

### 1.1 Log-Distance Path Loss Model
Wireless signal attenuation over distance $d$ in indoor environments is modeled using the standard IEEE Log-Distance Path Loss model:

$$PL(d) = PL(d_0) + 10 \cdot n \cdot \log_{10}\left(\frac{d}{d_0}\right) + X_\sigma$$

Where:
- $d_0 = 1.0\text{ m}$ (reference distance).
- $PL(d_0) = 40.0\text{ dB}$ (nominal free-space path loss at 1 meter for 2.4 GHz).
- $n = 2.8$ (path loss exponent for indoor office environments with light partitioning).
- $X_\sigma \sim \mathcal{N}(0, \sigma^2)$ (Gaussian shadow fading random variable representing multipath reflections and obstacle shadowing).

### 1.2 Received Signal Strength Indicator (RSSI)
The received power at the client antenna is:

$$\text{RSSI}(d) = P_{\text{tx}} - PL(d)$$

Clamped to standard Wi-Fi receiver sensitivity limits:
$$\text{RSSI}_{\text{clamped}} = \max\left(-95.0\text{ dBm}, \min\left(-30.0\text{ dBm}, \text{RSSI}(d)\right)\right)$$

### 1.3 Quality of Service (QoS) & Airtime Contention
As RSSI drops or channel utilization increases:
- **Modulation and Coding Scheme (MCS) Downshift**: Lower signal-to-noise ratio forces 802.11 radios to downgrade modulation (e.g. from 64-QAM to BPSK), increasing airtime transmission duration.
- **Latency Model**:
  $$\text{Latency} = \text{BaseLatency} + (\text{Load} \cdot 45\text{ ms}) + ((1 - S_{\text{signal}}) \cdot 35\text{ ms}) + \text{Jitter}$$
- **Packet Loss Model**:
  $$\text{LossRate} = \text{BaseLoss} + (\text{Load}^2 \cdot 0.12) + ((1 - S_{\text{signal}})^2 \cdot 0.25)$$

---

## 2. Switching Strategy 1: Basic (Greedy RSSI)

### 2.1 Principle
At every time step $t$, the client inspects all visible APs:

$$\text{AP}_{\text{target}} = \arg\max_{i \in \text{Visible APs}} \text{RSSI}_i(t)$$

If $\text{AP}_{\text{target}} \neq \text{AP}_{\text{current}}$, an immediate handoff is executed.

### 2.2 Academic Flaw (Viva Discussion)
In overlapping coverage boundaries where $\text{RSSI}_1 \approx \text{RSSI}_2$, random shadow fading $X_\sigma$ causes $\text{RSSI}_1$ and $\text{RSSI}_2$ to alternate which one is momentarily higher. This creates **ping-pong oscillations** (e.g., switching every 1–2 seconds), incurring frequent 100ms disconnection penalties and dropping TCP throughput.

---

## 3. Switching Strategy 2: Persistence-Based (Fixed Hysteresis)

### 3.1 Principle
Introduces a fixed hysteresis threshold $\Delta_{\text{hyst}}$ (typically $3.0\text{ dBm}$) and a dwell-time counter $K$ (e.g., $K=3$ consecutive steps).

A candidate $\text{AP}_{\text{cand}}$ qualifies if:

$$\text{RSSI}_{\text{cand}}(t) > \text{RSSI}_{\text{current}}(t) + \Delta_{\text{hyst}}$$

Condition:
$$\text{ConsecutiveCount}(\text{AP}_{\text{cand}}) \ge K$$

If the candidate drops below the margin before reaching $K$, the persistence counter resets to 0.

### 3.2 Limitations
1. **Static Margin**: Fixed $\Delta_{\text{hyst}}$ cannot adjust to varying noise environments. If shadow fading $\sigma > 3.5\text{ dB}$, fixed 3 dB hysteresis still flutters.
2. **Handoff Lag / Dead-Zone Drop**: If the client enters an elevator or sudden dead spot, the client waits $K$ steps before roaming, during which packets are completely dropped.
3. **QoS Blindness**: Completely ignores channel load and network congestion.

---

## 4. Switching Strategy 3: RoamWise (Adaptive Stability)

RoamWise combines statistical variance analysis, cross-layer health scoring, emergency fast-roam, and anti-ping-pong memory.

### 4.1 Real-Time Signal Variance & Adaptive Hysteresis
RoamWise maintains a sliding window of the last $W$ measurements ($W = 5$):

$$\mathcal{H}_{\text{RSSI}} = \{ \text{RSSI}(t - W + 1), \dots, \text{RSSI}(t) \}$$

The sample standard deviation $\sigma_{\text{RSSI}}$ is computed as:

$$\sigma_{\text{RSSI}} = \sqrt{\frac{1}{W - 1} \sum_{i=1}^W (\text{RSSI}_i - \mu)^2}$$

The adaptive hysteresis threshold dynamically expands:

$$\Delta_{\text{adaptive}}(t) = \Delta_{\text{base}} + \alpha \cdot \sigma_{\text{RSSI}}(t)$$

Where:
- $\Delta_{\text{base}} = 2.5\text{ dBm}$ (baseline margin).
- $\alpha = 1.2$ (fluctuation sensitivity multiplier).

*Interpretation*: In a calm environment ($\sigma \approx 0.5\text{ dB}$), $\Delta_{\text{adaptive}} \approx 3.1\text{ dBm}$. In a turbulent fading environment ($\sigma \approx 3.5\text{ dB}$), $\Delta_{\text{adaptive}}$ automatically widens to $6.7\text{ dBm}$, completely suppressing ping-pong flaps.

### 4.2 Cross-Layer Quality Score ($Q_{\text{AP}}$)
RoamWise normalizes physical, data link, and transport performance indicators into a composite score $Q \in [0.0, 1.0]$:

$$Q_{\text{AP}} = 0.45 \cdot S_{\text{RSSI}} + 0.20 \cdot (1 - S_{\text{lat}}) + 0.20 \cdot (1 - \text{Load}) + 0.15 \cdot (1 - S_{\text{loss}})$$

Where:
- $S_{\text{RSSI}} = \text{clamp}\left(\frac{\text{RSSI} - (-95)}{50}, 0, 1\right)$
- $S_{\text{lat}} = \text{clamp}\left(\frac{\text{Latency} - 5}{95}, 0, 1\right)$
- $\text{Load} \in [0.0, 1.0]$ (channel utilization from 802.11 BSS Load element)
- $S_{\text{loss}} = \text{clamp}\left(\frac{\text{PacketLossRate}}{0.30}, 0, 1\right)$

A handoff requires both $\text{RSSI}_{\text{cand}} > \text{RSSI}_{\text{current}} + \Delta_{\text{adaptive}}$ and $Q_{\text{cand}} > Q_{\text{current}} + 0.05$.

### 4.3 Emergency Fast-Roam Trigger
If the current link deteriorates catastrophically:

$$\text{RSSI}_{\text{current}}(t) < -82.0\text{ dBm} \quad \text{OR} \quad \text{PacketLossRate}_{\text{current}}(t) > 22\%$$

The normal dwell-time persistence is **bypassed immediately**. The client roams in a single step to the highest quality candidate, preventing session teardown.

### 4.4 Ping-Pong Suppression Memory
If an AP was deserted within the last $C$ time steps ($C = 4$), an additional damping penalty $\Delta_{\text{cooldown}} = +3.0\text{ dBm}$ is added to its required threshold, preventing rapid reciprocal returns.

---

## 5. Algorithmic Complexity

| Algorithm | Decision Time Complexity | Memory Complexity |
| :--- | :--- | :--- |
| **Basic (Greedy)** | $O(N)$ where $N$ is visible AP count | $O(1)$ |
| **Persistence** | $O(N)$ | $O(1)$ |
| **RoamWise** | $O(N + W)$ where $W$ is sliding window size | $O(N \cdot W)$ |

Because $N \le 16$ (visible Wi-Fi channels) and $W \le 10$, RoamWise runs in **sub-millisecond time (<0.05 ms)** on mobile embedded chipsets.
