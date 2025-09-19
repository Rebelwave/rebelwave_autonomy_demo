# app.py
import streamlit as st
import pandas as pd
import time
import plotly.graph_objects as go
import plotly.express as px

from simulation import Environment, create_fleet, state_snapshot
from autonomy import Autonomy
from utils import generate_waypoints_for_agents
from streamlit_plotly_events import plotly_events

st.set_page_config(page_title="RebelWaveTech - Autonomous Fleet Control Demo", layout="wide")
st.title("RebelWaveTech Autonomous Fleet Control — Demo")

# --- Sidebar controls ---
st.sidebar.header("Simulation Controls")
n_agents = st.sidebar.slider("Number of Agents", min_value=2, max_value=8, value=4)
n_obstacles = st.sidebar.slider("Number of Obstacles", min_value=0, max_value=10, value=5)
steps = st.sidebar.slider("Mission Steps (frames)", min_value=50, max_value=1000, value=300)
step_delay = st.sidebar.slider("Step delay (s)", min_value=0.05, max_value=1.0, value=0.12)
seed = st.sidebar.number_input("Random Seed", value=42)

start_button = st.sidebar.button("Start Mission")
stop_button = st.sidebar.button("Stop Mission")
regenerate_button = st.sidebar.button("Regenerate Environment")

# Failure injection
st.sidebar.header("Failure Simulation")
sensor_dropout_agent = st.sidebar.selectbox("Sensor Dropout (choose agent or None)", options=["None"] + [f"Agent_{i+1}" for i in range(8)])
dropout_when_step = st.sidebar.number_input("Dropout Step (frame)", min_value=0, value=150)
comm_loss_agent = st.sidebar.selectbox("Comms Loss (choose agent or None)", options=["None"] + [f"Agent_{i+1}" for i in range(8)])
comm_loss_step = st.sidebar.number_input("Comms Loss Step (frame)", min_value=0, value=200)

# --- Initialize environment, fleet, autonomy ---
if "env" not in st.session_state or regenerate_button:
    st.session_state.env = Environment(width=100, height=100, n_obstacles=n_obstacles, seed=seed)
    st.session_state.agents = create_fleet(n_agents=n_agents, env=st.session_state.env)
    st.session_state.waypoints = generate_waypoints_for_agents(n_agents=n_agents, env_width=100, env_height=100, n_waypoints=3)
    st.session_state.autonomy = Autonomy(st.session_state.env)
    st.session_state.running = False
    st.session_state.step = 0

# Update environment if controls changed
if n_obstacles != len(st.session_state.env.obstacles) or n_agents != len(st.session_state.agents):
    st.session_state.env = Environment(width=100, height=100, n_obstacles=n_obstacles, seed=seed)
    st.session_state.agents = create_fleet(n_agents=n_agents, env=st.session_state.env)
    st.session_state.waypoints = generate_waypoints_for_agents(n_agents=n_agents, env_width=100, env_height=100, n_waypoints=3)
    st.session_state.autonomy = Autonomy(st.session_state.env)
    st.session_state.step = 0
    st.session_state.running = False

# Assign some UI columns
col_map, col_details = st.columns([2, 1])

with col_details:
    st.subheader("Fleet Control Panel")
    st.markdown("Select an agent to inspect logs and assigned waypoints.")
    agent_ids = [a.id for a in st.session_state.agents]
    selected = st.selectbox("Select Agent", options=agent_ids)

    if st.button("Show Waypoints for Selected"):
        idx = int(selected.split("_")[1]) - 1
        st.write(st.session_state.waypoints[idx])

    st.markdown("**Control**")
    if start_button:
        st.session_state.running = True
    if stop_button:
        st.session_state.running = False

    st.markdown("**Logs (per-agent last messages)**")
    for a in st.session_state.agents:
        st.write(f"- {a.id}: mode={a.mode} | recent: { ' ; '.join(a.log[-3:]) }")

with col_map:
    st.subheader("Plant / Area Map (click an agent bubble)")
    # Build map data
    obs_df = st.session_state.env.obstacles_df()
    agent_df = pd.DataFrame([a.to_dict() for a in st.session_state.agents])

    fig = go.Figure()

    # Optional: show floorplan if exists
    try:
        # place a background image if floorplan.png exists
        fig.add_layout_image(
            dict(
                source="factory_floorplan_agents.png",
                xref="x", yref="y",
                x=0, y=100, sizex=100, sizey=100,
                sizing="stretch", opacity=0.5, layer="below"
            )
        )
    except Exception:
        pass

    # obstacles
    for _, r in obs_df.iterrows():
        fig.add_shape(
            type="circle",
            xref="x", yref="y",
            x0=r["x"]-r["r"], y0=r["y"]-r["r"],
            x1=r["x"]+r["r"], y1=r["y"]+r["r"],
            fillcolor="gray", opacity=0.4, line=dict(width=1)
        )

    # agent bubbles
    #colors = agent_df["mode"].map({"idle":"blue", "navigating":"green", "avoiding":"orange", "safe_mode":"red", "arrived":"purple", "lost_comms":"black"})
    #fig.add_trace(go.Scatter(
    #    x=agent_df["x"],
    #    y=agent_df["y"],
    #    mode="markers+text",
    #    text=agent_df["id"],
    #   textposition="top center",
    #   marker=dict(size=16, color=colors),
    #   hovertemplate="Agent: %{text}<br>Mode: %{marker.color}<extra></extra>"
    # Agents
        mode_colors = {"idle":"blue", "navigating":"green", "avoiding":"orange",
                   "safe_mode":"red", "arrived":"purple", "lost_comms":"black"
                   }
    
    colors = [mode_colors.get(m.mode, "blue") for m in st.session_state.agents]
    
    fig.add_trace(go.Scatter(
        x=agent_df["x"],
        y=agent_df["y"],
        mode="markers+text",
        text=agent_df["id"],
        textposition="top center",
        marker=dict(size=16, color=colors),
        hovertemplate="Agent: %{text}<br>Mode: %{marker.color}<extra></extra>"
    ))

    fig.update_layout(
        xaxis=dict(range=[0,100], visible=False),
        yaxis=dict(range=[0,100], visible=False, scaleanchor="x", scaleratio=1),
        height=700,
        title=f"Fleet Map - Step {st.session_state.step}"
    )
    st.plotly_chart(fig, use_container_width=True)

    selected_points = plotly_events(fig, click_event=True, select_event=False, override_height=700, key="map_events", override_width="100%"
                                    )
    if selected_points:
        clicked_idx = selected_points[0]["pointIndex"]
        clicked_agent = agent_df.iloc[clicked_idx]["id"]

        # Check for double-click (same agent clicked twice in a row)
        last_clicked = st.session.state.get("last_clicked_agent", None)
        if last_clicked == clicked_agent:
            st.session_state["zoom_agent"] = clicked_agent
        else:
            st.session_state["zoom_agent"] = None # reset zoom if switching agent

        st.session_state["selected_agent"] = clicked_agent
        st.session.state["last_clicked_agent"] = clicked_agent

    agent_ids = [a.id for a in st.session_state.agents]
    # if an agent was clicked, pre-select it
    if "selected_agent" in st.session_state:
        st.session.state["selected_agent"] = agent_ids[0]
        selected = st.selectbox("Select Agent", options=agent_ids, index=agent_ids.index(st.session_state["selected_agent"]["id"]))
     
     
           # --- Drilldown (Zoom View) ---
if "zoom_agent" in st.session_state and st.session_state["zoom_agent"]:
    zoom_agent_id = st.session_state["zoom_agent"]
    st.suybheader(f" Drilldown: {zoom_agent_id}")
    
    agent = next(a for a in st.session_state.agents if a.id == zoom_agent_id)
    idx = int(zoom_agent_id.split("_")[1]) - 1
    wp_list = st.session_state.waypoints[idx]
    obs_df = st.session_state.env.obstacles_df()

    fig_zoom = go.Figure()

    # 1. Plot trajectory history
    if agent.traj and len(agent.traj) > 1:
        xs, ys = zip(*agent.traj)
        fig_zoom.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", name="Trajectory",
            line=dict(color="blue", dash="dash")
        ))

    # 2. Plot waypoints
    if wp_list:
        xs, ys = zip(*wp_list)
        fig_zoom.add_trace(go.Scatter(
            x=xs, y=ys, mode="markers+lines", name="Waypoints",
            marker=dict(symbol="x", size=12, color="purple")
        ))

    # 3. Plot current agent position
    fig_zoom.add_trace(go.Scatter(
        x=[agent.x], y=[agent.y],
        mode="markers+text",
        text=[agent.id],
        textposition="top center",
        marker=dict(size=18, color="red", symbol="star"),
        name="Selected Agent"
    ))

    # 4. Plot nearby obstacles (within 20 units)
    for _, r in obs_df.iterrows():
        if abs(agent.x - r["x"]) < 20 and abs(agent.y - r["y"]) < 20:
            fig_zoom.add_shape(
                type="circle",
                xref="x", yref="y",
                x0=r["x"]-r["r"], y0=r["y"]-r["r"],
                x1=r["x"]+r["r"], y1=r["y"]+r["r"],
                fillcolor="gray", opacity=0.4, line=dict(width=1),
            )

    # 5. Set zoom window around the agent
    fig_zoom.update_layout(
        title=f"{zoom_agent_id} Local Area",
        xaxis=dict(range=[max(0, agent.x-25), min(100, agent.x+25)]),
        yaxis=dict(range=[max(0, agent.y-25), min(100, agent.y+25)], 
                   scaleanchor="x", scaleratio=1),
        height=500
    )

    st.plotly_chart(fig_zoom, use_container_width=True)
    
   
   
            # --- Simulation loop (synchronous) ---
if st.session_state.running:
    # loop for configured steps
    for s in range(st.session_state.step, steps):
        st.session_state.step = s
        # process agents
        for idx, agent in enumerate(st.session_state.agents):
            # determine whether this agent has failures
            sensor_ok = True
            comms_ok = True

            # sensor dropout injection
            if sensor_dropout_agent != "None" and agent.id == sensor_dropout_agent and s >= dropout_when_step:
                sensor_ok = False

            # comms loss injection
            if comm_loss_agent != "None" and agent.id == comm_loss_agent and s >= comm_loss_step:
                comms_ok = False
                agent.mode = "lost_comms"
                agent.log.append("Lost communications")

            # get current waypoint for agent
            wp_list = st.session_state.waypoints[idx]
            # choose waypoint index by checking if arrived
            # we'll pick the first waypoint not reached
            target_wp = None
            for wp in wp_list:
                if (abs(agent.x - wp[0]) > 1.5) or (abs(agent.y - wp[1]) > 1.5):
                    target_wp = wp
                    break
            if target_wp is None:
                # all arrived; idle
                agent.mode = "arrived"
                agent.vx = 0; agent.vy = 0
                continue

            # If comms lost, do not update position (simulate stuck)
            if not comms_ok:
                agent.log.append("Comms lost -> holding position")
                continue

            # autonomy compute
            new_x, new_y, mode, reason = st.session_state.autonomy.compute_control(
                agent, waypoint=target_wp, dt=1.0, sensor_ok=sensor_ok
            )
            agent.x = new_x
            agent.y = new_y

            # explainable logging: store brief reason
            if reason == "avoid_obstacle":
                agent.log.append(f"Step {s}: avoided obstacle")
            elif reason == "follow_wp":
                agent.log.append(f"Step {s}: following waypoint")
            elif reason == "sensor_dropout":
                agent.log.append(f"Step {s}: sensor dropout -> safe_mode")

        # Render update UI
        # Fleet map refresh (reuse plotting code quickly)
        agent_df = pd.DataFrame([a.to_dict() for a in st.session_state.agents])
        obs_df = st.session_state.env.obstacles_df()

        fig2 = go.Figure()
        # background image try
        try:
            fig2.add_layout_image(
                dict(
                    source="floorplan.png",
                    xref="x", yref="y",
                    x=0, y=100, sizex=100, sizey=100,
                    sizing="stretch", opacity=0.5, layer="below"
                )
            )
        except Exception:
            pass

        for _, r in obs_df.iterrows():
            fig2.add_shape(
                type="circle",
                xref="x", yref="y",
                x0=r["x"]-r["r"], y0=r["y"]-r["r"],
                x1=r["x"]+r["r"], y1=r["y"]+r["r"],
                fillcolor="gray", opacity=0.4, line=dict(width=1)
            )

        mode_colors = {
            "idle":"blue", "navigating":"green", "avoiding":"orange",
            "safe_mode":"red", "arrived":"purple", "lost_comms":"black"
        }
        colors = [mode_colors.get(m.mode, "blue") for m in st.session_state.agents]

        fig2.add_trace(go.Scatter(
            x=agent_df["x"],
            y=agent_df["y"],
            mode="markers+text",
            text=agent_df["id"],
            textposition="top center",
            marker=dict(size=16, color=colors),
            hovertemplate="Agent: %{text}<br>Mode: %{marker.color}<extra></extra>"
        ))

        fig2.update_layout(xaxis=dict(range=[0,100], visible=False),
                           yaxis=dict(range=[0,100], visible=False, scaleanchor="x", scaleratio=1),
                           height=700, title=f"Fleet Map - Step {st.session_state.step}")
        # use a placeholder to update map in-place
        map_placeholder = st.empty()
        map_placeholder.plotly_chart(fig2, use_container_width=True)

        # show details for selected agent
        sel_agent = next((a for a in st.session_state.agents if a.id == selected), None)
        if sel_agent:
            st.sidebar.markdown(f"**Selected: {sel_agent.id}**")
            st.sidebar.write(f"Mode: {sel_agent.mode}")
            st.sidebar.write(f"Position: ({sel_agent.x:.1f},{sel_agent.y:.1f})")
            st.sidebar.write("Recent log:")
            for msg in sel_agent.log[-6:]:
                st.sidebar.write(f"- {msg}")

        time.sleep(step_delay)

        # break early if stop clicked (Streamlit can't update a variable mid-loop from UI easily)
        if not st.session_state.running:
            break

    # mission finished or stopped
    st.session_state.running = False
    st.success("Mission ended / stopped")
else:
    st.info("Press **Start Mission** to play the mission (synchronous demo).")