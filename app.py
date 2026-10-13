"""
RoamWise — A Smart Wi-Fi Handoff Stability Simulator
===================================================
Streamlit Interactive Dashboard for Network Simulation and Performance Analysis.
Designed for Third-Year IT Engineering Viva and Project Demonstrations.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, Any, List, Tuple, Optional

from access_point import AccessPoint
from handoff_algorithms import (
    BasicSignalHandoff,
    PersistenceHandoff,
    RoamWiseHandoff
)
from scenarios import (
    Scenario,
    get_all_scenarios,
    create_custom_scenario
)
from simulator import Simulator, SimulationResult
from metrics import SimulationMetricsSummary

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION & CUSTOM STYLES
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="RoamWise — Wi-Fi Handoff Simulator",
    page_icon="📶",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for rich aesthetics and faculty-friendly layout
st.markdown("""
<style>
    /* Metric Cards Styling */
    .metric-box {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 12px;
        padding: 18px 20px;
        margin-bottom: 15px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    .metric-title {
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #94a3b8;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 1.85rem;
        font-weight: 700;
        color: #38bdf8;
    }
    .metric-sub {
        font-size: 0.8rem;
        color: #64748b;
        margin-top: 4px;
    }
    .badge-basic {
        background-color: #ef4444;
        color: white;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.75rem;
    }
    .badge-persistence {
        background-color: #f59e0b;
        color: white;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.75rem;
    }
    .badge-roamwise {
        background-color: #10b981;
        color: white;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.75rem;
    }
    .header-banner {
        padding: 16px 20px;
        border-radius: 12px;
        background: linear-gradient(90deg, #1e293b 0%, #0f172a 100%);
        border-left: 5px solid #0284c7;
        margin-bottom: 24px;
    }
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# SIDEBAR CONTROLS
# -----------------------------------------------------------------------------
st.sidebar.image("https://img.icons8.com/fluency/96/wifi-router.png", width=64)
st.sidebar.title("RoamWise Control")
st.sidebar.caption("Wi-Fi Mobility & Handoff Stability Engine")

scenario_options = {
    "1. Stable Linear Walk": "stable_linear_walk",
    "2. Fluctuating Signals (Ping-Pong)": "fluctuating_boundary",
    "3. Deteriorating Connection (Obstacle)": "deteriorating_connection",
    "4. Congested Hotspot (QoS Test)": "congested_hotspot",
    "5. Custom Scenario": "custom"
}

selected_label = st.sidebar.selectbox(
    "Select Test Scenario:",
    list(scenario_options.keys()),
    index=1
)
scenario_choice = scenario_options[selected_label]

st.sidebar.markdown("---")
st.sidebar.subheader("Simulation Parameters")
seed_val = st.sidebar.number_input("Random Seed (Reproducibility):", min_value=1, max_value=9999, value=42, step=1)

# Custom Scenario Parameters
if scenario_choice == "custom":
    st.sidebar.markdown("#### Custom Environment Setup")
    custom_duration = st.sidebar.slider("Duration (seconds/steps):", 30, 120, 75)
    custom_speed = st.sidebar.slider("Client Speed (m/s):", 0.5, 3.0, 1.0, step=0.1)
    custom_noise = st.sidebar.slider("Shadow Fading Noise σ (dB):", 0.0, 5.0, 2.8, step=0.2)
    st.sidebar.markdown("#### Access Point Loads")
    ap1_l = st.sidebar.slider("AP-1 Channel Load:", 0.0, 1.0, 0.25, 0.05)
    ap2_l = st.sidebar.slider("AP-2 Channel Load:", 0.0, 1.0, 0.30, 0.05)
    ap3_l = st.sidebar.slider("AP-3 Channel Load:", 0.0, 1.0, 0.20, 0.05)

st.sidebar.markdown("---")
st.sidebar.subheader("Strategy Tuning")

with st.sidebar.expander("Persistence Tuning", expanded=False):
    pers_hyst = st.slider("Hysteresis Margin (dBm):", 1.0, 6.0, 3.0, 0.5)
    pers_dwell = st.slider("Dwell Steps (K):", 1, 6, 3, 1)

with st.sidebar.expander("RoamWise Tuning", expanded=False):
    rw_base_hyst = st.slider("Base Hysteresis (dBm):", 1.0, 5.0, 2.5, 0.5)
    rw_alpha = st.slider("Fluctuation Scaling (α):", 0.5, 2.5, 1.2, 0.1)
    rw_window = st.slider("Sliding Window Size (W):", 3, 10, 5, 1)
    rw_cutoff = st.slider("Emergency Cutoff (dBm):", -90.0, -75.0, -82.0, 1.0)


# -----------------------------------------------------------------------------
# SIMULATION EXECUTION (Fast real-time computation without stale disk cache)
# -----------------------------------------------------------------------------
def execute_simulation(
    scen_key: str,
    seed: int,
    pers_hyst: float,
    pers_dwell: int,
    rw_base_hyst: float,
    rw_alpha: float,
    rw_window: int,
    rw_cutoff: float,
    custom_args: tuple = ()
) -> Tuple[Scenario, Dict[str, Any], Dict[str, pd.DataFrame]]:
    sim = Simulator(seed=seed)

    if scen_key == "custom":
        dur, spd, noise, l1, l2, l3 = custom_args
        scen = create_custom_scenario(
            duration_steps=dur,
            client_speed_mps=spd,
            shadow_fading_std=noise,
            ap1_load=l1,
            ap2_load=l2,
            ap3_load=l3,
            seed=seed
        )
    else:
        scenarios_dict = get_all_scenarios(seed=seed)
        scen = scenarios_dict[scen_key]

    # Instantiate strategies with user parameters
    algos = [
        BasicSignalHandoff(margin_dbm=0.0),
        PersistenceHandoff(hysteresis_dbm=pers_hyst, dwell_steps=pers_dwell),
        RoamWiseHandoff(
            base_hysteresis_dbm=rw_base_hyst,
            fluctuation_alpha=rw_alpha,
            window_size=rw_window,
            emergency_rssi_cutoff=rw_cutoff
        )
    ]

    results = sim.run_comparison(scenario=scen, algorithms=algos)

    # Convert to DataFrames
    dfs = {}
    for name, res in results.items():
        dfs[name] = pd.DataFrame(res.time_series)

    return scen, results, dfs


# Gather custom args tuple
custom_args = (
    (custom_duration, custom_speed, custom_noise, ap1_l, ap2_l, ap3_l)
    if scenario_choice == "custom" else ()
)

scenario, results, dfs = execute_simulation(
    scenario_choice,
    seed_val,
    pers_hyst,
    pers_dwell,
    rw_base_hyst,
    rw_alpha,
    rw_window,
    rw_cutoff,
    custom_args
)

# Extract algorithm keys
BASIC_KEY = "Basic (Signal-Only)"
PERS_KEY = "Persistence-Based (Fixed Hysteresis)"
RW_KEY = "RoamWise (Adaptive & Stability-Aware)"

basic_res = results[BASIC_KEY]
pers_res = results[PERS_KEY]
rw_res = results[RW_KEY]


# -----------------------------------------------------------------------------
# MAIN HEADER
# -----------------------------------------------------------------------------
st.markdown(f"""
<div class="header-banner">
    <h2 style="margin:0; color:#f8fafc; font-size:1.6rem;">📶 RoamWise: Smart Wi-Fi Handoff Stability Simulator</h2>
    <p style="margin:5px 0 0 0; color:#94a3b8; font-size:0.95rem;">
        Currently Simulating: <strong>{scenario.title}</strong> — 
        Comparing greedy RSSI, classic hysteresis dwell time, and RoamWise adaptive stability.
    </p>
</div>
""", unsafe_allow_html=True)

st.info(f"💡 **Scenario Overview**: {scenario.description}")


# -----------------------------------------------------------------------------
# TABS INTERFACE
# -----------------------------------------------------------------------------
tab_overview, tab_charts, tab_events, tab_comparison, tab_viva = st.tabs([
    "📊 Performance Dashboard",
    "📈 Signal & QoS Graphs",
    "📝 Handoff Event Log",
    "🗺️ Network Map & AP Details",
    "🎓 Viva Guide & Networking Theory"
])


# =============================================================================
# TAB 1: PERFORMANCE DASHBOARD
# =============================================================================
with tab_overview:
    st.subheader("Key Performance Comparison")

    # 4 Metric Cards Comparison Grid
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-title">Total Handoffs</div>
            <div class="metric-value">{rw_res.summary.handoff_count}</div>
            <div class="metric-sub">
                Basic: <span style="color:#ef4444">{basic_res.summary.handoff_count}</span> | 
                Persistence: <span style="color:#f59e0b">{pers_res.summary.handoff_count}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        diff_pp = basic_res.summary.ping_pong_count - rw_res.summary.ping_pong_count
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-title">Ping-Pong Oscillations</div>
            <div class="metric-value" style="color: {'#10b981' if rw_res.summary.ping_pong_count == 0 else '#38bdf8'};">
                {rw_res.summary.ping_pong_count}
            </div>
            <div class="metric-sub">
                Basic: <span style="color:#ef4444">{basic_res.summary.ping_pong_count}</span> | 
                Eliminated: <strong>{diff_pp}</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-title">Packet Delivery Ratio</div>
            <div class="metric-value">{rw_res.summary.packet_delivery_ratio_pct:.1f}%</div>
            <div class="metric-sub">
                Basic: {basic_res.summary.packet_delivery_ratio_pct:.1f}% | 
                Persistence: {pers_res.summary.packet_delivery_ratio_pct:.1f}%
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-title">Handoff Disruption Time</div>
            <div class="metric-value">{rw_res.summary.total_interruption_time_ms:.0f} ms</div>
            <div class="metric-sub">
                Basic: {basic_res.summary.total_interruption_time_ms:.0f} ms | 
                Persistence: {pers_res.summary.total_interruption_time_ms:.0f} ms
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### Summary Scorecard Table")

    scorecard_data = []
    for res in [basic_res, pers_res, rw_res]:
        s = res.summary
        scorecard_data.append({
            "Strategy": s.algorithm_name,
            "Total Handoffs": s.handoff_count,
            "Ping-Pongs": s.ping_pong_count,
            "Ping-Pong %": f"{s.ping_pong_ratio_pct:.1f}%",
            "Avg RSSI (dBm)": f"{s.avg_rssi_dbm:.1f}",
            "Avg Latency (ms)": f"{s.avg_latency_ms:.1f}",
            "P95 Latency (ms)": f"{s.p95_latency_ms:.1f}",
            "PDR (%)": f"{s.packet_delivery_ratio_pct:.2f}%",
            "Interruption Delay": f"{s.total_interruption_time_ms:.0f} ms",
            "Stability Index": f"{s.stability_score_pct:.1f}%",
            "QoE MOS (1-5)": f"{s.qoe_score:.2f} ⭐"
        })

    score_df = pd.DataFrame(scorecard_data)
    st.dataframe(score_df, use_container_width=True, hide_index=True)

    # Bar Charts Comparison
    st.markdown("### Visual Metrics Breakdown")
    c_b1, c_b2 = st.columns(2)

    with c_b1:
        fig_bar_h = go.Figure(data=[
            go.Bar(
                name="Total Handoffs",
                x=["Basic (Signal-Only)", "Persistence", "RoamWise"],
                y=[basic_res.summary.handoff_count, pers_res.summary.handoff_count, rw_res.summary.handoff_count],
                marker_color=["#ef4444", "#f59e0b", "#10b981"],
                text=[basic_res.summary.handoff_count, pers_res.summary.handoff_count, rw_res.summary.handoff_count],
                textposition='auto',
            ),
            go.Bar(
                name="Ping-Pong Flaps",
                x=["Basic (Signal-Only)", "Persistence", "RoamWise"],
                y=[basic_res.summary.ping_pong_count, pers_res.summary.ping_pong_count, rw_res.summary.ping_pong_count],
                marker_color=["#991b1b", "#b45309", "#047857"],
                text=[basic_res.summary.ping_pong_count, pers_res.summary.ping_pong_count, rw_res.summary.ping_pong_count],
                textposition='auto',
            )
        ])
        fig_bar_h.update_layout(
            title="Handoff Count vs Unnecessary Ping-Pong Flapping",
            barmode="group",
            height=340,
            margin=dict(l=20, r=20, t=40, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_bar_h, use_container_width=True)

    with c_b2:
        fig_bar_qoe = go.Figure(data=[
            go.Bar(
                name="Packet Delivery Ratio (%)",
                x=["Basic", "Persistence", "RoamWise"],
                y=[basic_res.summary.packet_delivery_ratio_pct, pers_res.summary.packet_delivery_ratio_pct, rw_res.summary.packet_delivery_ratio_pct],
                marker_color="#38bdf8",
                text=[f"{s.packet_delivery_ratio_pct:.1f}%" for s in [basic_res.summary, pers_res.summary, rw_res.summary]],
                textposition='auto'
            ),
            go.Bar(
                name="Stability Score (%)",
                x=["Basic", "Persistence", "RoamWise"],
                y=[basic_res.summary.stability_score_pct, pers_res.summary.stability_score_pct, rw_res.summary.stability_score_pct],
                marker_color="#818cf8",
                text=[f"{s.stability_score_pct:.1f}%" for s in [basic_res.summary, pers_res.summary, rw_res.summary]],
                textposition='auto'
            )
        ])
        fig_bar_qoe.update_layout(
            title="Packet Delivery Ratio & Network Stability Index",
            barmode="group",
            height=340,
            margin=dict(l=20, r=20, t=40, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_bar_qoe, use_container_width=True)


# =============================================================================
# TAB 2: SIGNAL & QOS TIME-SERIES GRAPHS
# =============================================================================
with tab_charts:
    st.subheader("Signal Strength (RSSI) & Roaming Dynamics Over Time")

    # Time series of AP Signals with Handoff Events
    fig_rssi = go.Figure()

    # Base AP signal traces from common trace
    df_sample = dfs[RW_KEY]
    fig_rssi.add_trace(go.Scatter(
        x=df_sample["time_s"], y=df_sample["ap1_rssi"],
        mode="lines", name="AP-1 Beacon RSSI",
        line=dict(color="#3b82f6", dash="dot", width=1.5),
        opacity=0.7
    ))
    fig_rssi.add_trace(go.Scatter(
        x=df_sample["time_s"], y=df_sample["ap2_rssi"],
        mode="lines", name="AP-2 Beacon RSSI",
        line=dict(color="#10b981", dash="dot", width=1.5),
        opacity=0.7
    ))
    fig_rssi.add_trace(go.Scatter(
        x=df_sample["time_s"], y=df_sample["ap3_rssi"],
        mode="lines", name="AP-3 Beacon RSSI",
        line=dict(color="#f59e0b", dash="dot", width=1.5),
        opacity=0.7
    ))

    # Active connected RSSI for each algorithm
    colors = {BASIC_KEY: "#ef4444", PERS_KEY: "#f97316", RW_KEY: "#06b6d4"}
    for name, df in dfs.items():
        fig_rssi.add_trace(go.Scatter(
            x=df["time_s"], y=df["rssi_dbm"],
            mode="lines", name=f"Active: {name}",
            line=dict(color=colors[name], width=2.5)
        ))

    # Add handoff marker flags
    for res, color, symbol in [(basic_res, "#ef4444", "circle-x"), (pers_res, "#f97316", "triangle-up"), (rw_res, "#06b6d4", "star")]:
        handoff_steps = [e.step for e in res.handoff_events]
        if handoff_steps:
            sub_df = dfs[res.algorithm_name][dfs[res.algorithm_name]["step"].isin(handoff_steps)]
            fig_rssi.add_trace(go.Scatter(
                x=sub_df["time_s"], y=sub_df["rssi_dbm"],
                mode="markers",
                name=f"Handoff ({res.algorithm_name})",
                marker=dict(symbol=symbol, size=10, color=color, line=dict(width=1, color="white")),
                hovertext=[e.reason for e in res.handoff_events],
                hoverinfo="text+x+y"
            ))

    fig_rssi.update_layout(
        title="Received Signal Strength (RSSI) Trajectory and Handoff Trigger Points",
        xaxis_title="Simulation Time (seconds)",
        yaxis_title="RSSI (dBm)",
        height=450,
        hovermode="x unified",
        margin=dict(l=20, r=20, t=40, b=20)
    )
    st.plotly_chart(fig_rssi, use_container_width=True)

    # Secondary Charts: Latency & Adaptive Threshold Telemetry
    c_g1, c_g2 = st.columns(2)

    with c_g1:
        fig_lat = go.Figure()
        for name, df in dfs.items():
            fig_lat.add_trace(go.Scatter(
                x=df["time_s"], y=df["latency_ms"],
                mode="lines", name=name,
                line=dict(color=colors[name], width=2)
            ))
        fig_lat.update_layout(
            title="Experienced End-to-End Latency Over Time (ms)",
            xaxis_title="Time (s)",
            yaxis_title="Latency (ms)",
            height=340,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig_lat, use_container_width=True)

    with c_g2:
        df_rw = dfs[RW_KEY]
        fig_adapt = go.Figure()
        fig_adapt.add_trace(go.Scatter(
            x=df_rw["time_s"], y=df_rw["adaptive_margin_dbm"],
            mode="lines", name="RoamWise Adaptive Margin (dBm)",
            line=dict(color="#10b981", width=2.2)
        ))
        fig_adapt.add_trace(go.Scatter(
            x=df_rw["time_s"], y=df_rw["signal_std"],
            mode="lines", name="Signal Standard Deviation σ (dB)",
            line=dict(color="#a855f7", width=1.8, dash="dash")
        ))
        fig_adapt.update_layout(
            title="RoamWise Internal Telemetry (Adaptive Margin vs Signal Variance)",
            xaxis_title="Time (s)",
            yaxis_title="Margin / Std Dev (dB)",
            height=340,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig_adapt, use_container_width=True)


# =============================================================================
# TAB 3: HANDOFF EVENT LOG
# =============================================================================
with tab_events:
    st.subheader("Handoff Transition Logs")
    st.markdown("Detailed breakdown of every AP switch, trigger condition, and whether ping-pong oscillation occurred.")

    filter_algo = st.selectbox("Filter by Algorithm:", ["All Algorithms", BASIC_KEY, PERS_KEY, RW_KEY])

    all_event_rows = []
    for res in [basic_res, pers_res, rw_res]:
        if filter_algo != "All Algorithms" and res.algorithm_name != filter_algo:
            continue
        for e in res.handoff_events:
            all_event_rows.append({
                "Step / Time (s)": e.step,
                "Algorithm": res.algorithm_name,
                "Transition": f"{e.from_ap} ➔ {e.to_ap}",
                "Ping-Pong?": "⚠️ YES" if e.is_ping_pong else "✅ No",
                "Disruption (ms)": f"{e.disruption_ms:.0f} ms",
                "Trigger Reason": e.reason
            })

    if all_event_rows:
        events_df = pd.DataFrame(all_event_rows)
        st.dataframe(events_df, use_container_width=True, hide_index=True)
    else:
        st.success("No handoffs occurred for this filter selection! (Zero connection disruption)")

    # CSV Download Section
    st.markdown("---")
    st.subheader("📥 Export Simulation Data")
    c_dl1, c_dl2 = st.columns(2)

    with c_dl1:
        # Full time series export
        combined_ts = []
        for name, df in dfs.items():
            df_copy = df.copy()
            df_copy["algorithm"] = name
            combined_ts.append(df_copy)
        full_ts_df = pd.concat(combined_ts, ignore_index=True)
        csv_ts = full_ts_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Full Time-Series Telemetry (CSV)",
            data=csv_ts,
            file_name=f"roamwise_{scenario.scenario_id}_timeseries.csv",
            mime="text/csv"
        )

    with c_dl2:
        csv_scores = score_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Metrics Summary Table (CSV)",
            data=csv_scores,
            file_name=f"roamwise_{scenario.scenario_id}_summary.csv",
            mime="text/csv"
        )


# =============================================================================
# TAB 4: NETWORK MAP & AP DETAILS
# =============================================================================
with tab_comparison:
    st.subheader("Physical Topology & Client Trajectory Map")
    st.caption("2D Floor Plan layout showing Access Points, coverage zones, and mobile user motion path.")

    # 2D Map using Plotly
    fig_map = go.Figure()

    # Draw AP Coverage circles & markers
    ap_colors = {"AP-1": "#3b82f6", "AP-2": "#10b981", "AP-3": "#f59e0b"}
    for ap in scenario.access_points:
        # Coverage radius (nominal 25 meters)
        fig_map.add_shape(
            type="circle",
            xref="x", yref="y",
            x0=ap.x - 22, y0=ap.y - 22,
            x1=ap.x + 22, y1=ap.y + 22,
            fillcolor=ap_colors.get(ap.ap_id, "#64748b"),
            opacity=0.12,
            line=dict(color=ap_colors.get(ap.ap_id, "#64748b"), dash="dash", width=1)
        )
        # AP Point
        fig_map.add_trace(go.Scatter(
            x=[ap.x], y=[ap.y],
            mode="markers+text",
            text=[f"<b>{ap.ap_id}</b><br>Ch {ap.channel} (Load: {ap.load_factor*100:.0f}%)"],
            textposition="top center",
            marker=dict(size=16, color=ap_colors.get(ap.ap_id, "#64748b"), symbol="square"),
            name=f"{ap.ap_id} ({ap.ssid})"
        ))

    # Draw Trajectory
    traj_x = [pt[0] for pt in scenario.trajectory]
    traj_y = [pt[1] for pt in scenario.trajectory]
    fig_map.add_trace(go.Scatter(
        x=traj_x, y=traj_y,
        mode="lines+markers",
        name="Mobile Client Trajectory",
        line=dict(color="#f43f5e", width=2.5),
        marker=dict(size=4, color="#f43f5e")
    ))

    # Mark Start and End points
    fig_map.add_trace(go.Scatter(
        x=[traj_x[0]], y=[traj_y[0]],
        mode="markers+text",
        text=["🟢 Start"],
        textposition="bottom left",
        marker=dict(size=12, color="#22c55e"),
        name="Trajectory Start"
    ))
    fig_map.add_trace(go.Scatter(
        x=[traj_x[-1]], y=[traj_y[-1]],
        mode="markers+text",
        text=["🔴 End"],
        textposition="bottom right",
        marker=dict(size=12, color="#ef4444"),
        name="Trajectory End"
    ))

    fig_map.update_layout(
        title="2D Physical Floor Plan & AP Radio Propagation Layout",
        xaxis=dict(title="X Position (meters)", range=[-5, 105]),
        yaxis=dict(title="Y Position (meters)", range=[-5, 45]),
        height=480,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    st.plotly_chart(fig_map, use_container_width=True)

    # Detailed AP Specs Table
    st.markdown("### Access Point Hardware Specifications")
    ap_data = []
    for ap in scenario.access_points:
        ap_data.append({
            "AP ID": ap.ap_id,
            "SSID": ap.ssid,
            "Channel": ap.channel,
            "Frequency": f"{ap.frequency_ghz} GHz",
            "Tx Power": f"{ap.tx_power_dbm} dBm",
            "Coordinates": f"({ap.x:.1f}m, {ap.y:.1f}m)",
            "Channel Load": f"{ap.load_factor*100:.0f}%",
            "Base Latency": f"{ap.base_latency_ms} ms",
            "Path Loss Exponent (n)": ap.path_loss_exponent
        })
    st.table(pd.DataFrame(ap_data))


# =============================================================================
# TAB 5: VIVA GUIDE & NETWORKING THEORY
# =============================================================================
with tab_viva:
    st.subheader("🎓 Faculty Viva Defense & Theoretical Foundations")
    st.markdown("""
    Use this section to prepare for examiner questions during your IT engineering project evaluation.
    """)

    with st.expander("1. What is the Wi-Fi Handoff (Roaming) Problem?", expanded=True):
        st.markdown("""
        - **Definition**: Wi-Fi roaming occurs when a mobile station (STA) transitions its association from one Access Point (AP) to another within the same Extended Service Set (ESS / SSID) without breaking user session continuity.
        - **Why it matters**: In real-time applications (VoIP calls, Zoom, online gaming, industrial AGVs), a roaming handoff must be seamless. If handoff takes >100ms or drops packets, audio glitches and connection stalls occur.
        - **The Challenge**: The client decides when to switch based on noisy wireless signals. Too sensitive = ping-pong oscillations; too conservative = sudden dead-zone disconnection.
        """)

    with st.expander("2. What is the 'Ping-Pong Effect' and why is it harmful?", expanded=True):
        st.markdown("""
        - **Ping-Pong Effect**: Rapid, back-and-forth handoff oscillations between two APs (e.g., $AP_1 \\rightarrow AP_2 \\rightarrow AP_1 \\rightarrow AP_2$) occurring over a short time interval.
        - **Cause**: In coverage overlap zones, signal strength naturally fluctuates due to multipath fading, moving people, and constructive/destructive interference. A naive RSSI-only algorithm switches whenever one AP briefly spikes above another.
        - **Impact on Network Performance**:
          1. **Airtime Waste**: Management frame flooding (Probe Requests, Authentications, Reassociations).
          2. **Packet Loss**: During the 80–150ms reassociation gap, inflight packets are dropped or retransmitted.
          3. **TCP Throughput Collapse**: Packet drops trigger TCP Fast Retransmit and Congestion Window (cwnd) collapse.
        """)

    with st.expander("3. How does RoamWise mathematically solve this?", expanded=True):
        st.markdown("""
        RoamWise introduces three mathematical and engineering enhancements:
        
        1. **Adaptive Hysteresis Threshold based on Moving Variance**:
           $$\\Delta_{\\text{adaptive}} = \\Delta_{\\text{base}} + \\alpha \\cdot \\sigma_{\\text{RSSI}}$$
           where $\\sigma_{\\text{RSSI}}$ is the sample standard deviation of RSSI over sliding window $W$. When channel volatility rises, the threshold expands dynamically, preventing noise from triggering handoffs.
           
        2. **Cross-Layer Composite Quality Score ($Q_{\\text{AP}}$)**:
           Instead of relying purely on physical layer RSSI, RoamWise incorporates data-link and network layer telemetry:
           $$Q_{\\text{AP}} = 0.45 \\cdot S_{\\text{RSSI}} + 0.20 \\cdot (1 - S_{\\text{latency}}) + 0.20 \\cdot (1 - \\text{Load}) + 0.15 \\cdot (1 - \\text{Loss})$$
           This prevents connecting to a "loud but congested" AP!
           
        3. **Emergency Fast-Roam Failover**:
           If current signal falls below critical sensitivity ($-82$ dBm) or packet loss $> 22\\%$, the dwell timer is immediately bypassed to save the active connection.
        """)

    with st.expander("4. How does RoamWise relate to IEEE Standards (802.11k, 802.11v, 802.11r)?"):
        st.markdown("""
        - **IEEE 802.11r (Fast BSS Transition - FT)**: Eliminates 4-way handshake delay on secure networks, reducing physical handoff disruption to $<50$ms.
        - **IEEE 802.11k (Radio Resource Measurement - RRM)**: Provides Neighbor Reports so the client doesn't waste time scanning all 14+ channels.
        - **IEEE 802.11v (BSS Transition Management - BTM)**: Allows the AP infrastructure to send network load suggestions to the client.
        - **RoamWise's role**: Standards define **mechanisms** (how to exchange frames), but the **decision logic** (when and where to roam) is left entirely to client vendor algorithms. RoamWise is a client-side decision engine!
        """)

    with st.expander("5. Simulation Assumptions and Limitations"):
        st.markdown("""
        - **Path Loss Model**: Standard Log-Distance Path Loss model ($n=2.8$, $PL(d_0)=40$ dB) with zero-mean Gaussian shadow fading.
        - **Time Granularity**: Discrete time steps of 1.0 second per measurement cycle.
        - **Handoff Penalty**: Simulated 100 ms unmanaged association gap causing 15% transient packet loss penalty during handoff steps.
        - **Station Hardware**: Single Wi-Fi interface (hard handoff / break-before-make model).
        """)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #64748b; font-size: 0.85rem;'>"
    "RoamWise — Built with Python, Streamlit, Pandas, and Plotly for IT Engineering Academic Demonstrations."
    "</div>",
    unsafe_allow_html=True
)
