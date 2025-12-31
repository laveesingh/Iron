import streamlit as st
import pandas as pd
from datetime import date
import sys
import os

# Add scripts directory to path to import data_manager
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))
import data_manager as dm

st.set_page_config(page_title="Project Iron", page_icon="💪", layout="wide")

st.title("Project Iron 💪")

# Tabs
tab1, tab2, tab3 = st.tabs(["Dashboard", "Daily Tracker", "Research & Plans"])

# --- DASHBOARD ---
with tab1:
    st.header("Active Goals")
    goals = dm.load_goals()

    active_goals = [g for g in goals if g.get("status", "active") == "active"]
    
    if not active_goals:
        st.info("No active goals found in `data/goals.yaml`.")
        active_goals = []

    cols = st.columns(max(1, len(active_goals)))
    for i, goal in enumerate(active_goals):
        with cols[i]:
            st.subheader(goal['name'])
            st.write(f"**Target:** {goal['target']}")
            st.caption(goal['description'])
            
            for metric in goal.get('metrics', []):
                current = dm.resolve_metric_current(metric)
                unit = metric.get('unit', '')
                target = metric.get('target', '')
                st.metric(label=metric['name'], value=f"{current:.0f} {unit}".strip(), delta=f"Target: {target} {unit}".strip())

                if metric.get("editable"):
                    key = f"metric_{goal.get('id')}_{metric.get('name')}"
                    new_val = st.number_input(
                        f"Update {metric['name']}",
                        value=float(metric.get('current', 0) or 0),
                        step=1.0,
                        key=key,
                    )
                    if st.button("Save", key=f"save_{key}"):
                        dm.update_goal_metric_current(goal.get('id'), metric.get('name'), new_val)
                        st.success("Saved.")
                        st.rerun()

    st.divider()
    st.header("Recent Activity")
    logs = dm.get_logs()
    if not logs.empty:
        st.dataframe(logs.tail(10), width="stretch")
    else:
        st.info("No activity logged yet.")

# --- TRACKER ---
with tab2:
    st.header("Daily Tracker")
    selected_date = st.date_input("Date", date.today())
    date_str = selected_date.strftime("%Y-%m-%d")
    
    routines = dm.load_routines()
    daily_routines = routines.get('daily', [])
    weekly_routines = routines.get('weekly', [])
    
    # Get existing status for this date
    existing_status = dm.get_daily_status(date_str)
    
    with st.form("daily_log_form"):
        st.subheader("Daily Habits")
        
        form_data = {}
        for habit in daily_routines:
            habit_type = habit.get("type", "bool")
            habit_id = habit["id"]
            label = habit["name"]
            if habit_type == "number":
                cur = existing_status.get(habit_id)
                try:
                    cur_val = float(cur) if cur is not None else 0.0
                except Exception:
                    cur_val = 0.0
                unit = habit.get("unit", "")
                target = habit.get("target")
                help_text = None
                if target is not None:
                    help_text = f"Target: {target} {unit}".strip()
                val = st.number_input(f"{label} ({unit})".strip(), value=cur_val, step=1.0, help=help_text)
                form_data[habit_id] = val
            else:
                is_checked = st.checkbox(label, value=bool(existing_status.get(habit_id)))
                form_data[habit_id] = int(is_checked)
            
        submitted = st.form_submit_button("Log Day")
        
        if submitted:
            for habit_id, value in form_data.items():
                dm.log_entry(date_str, habit_id, value)
            st.success(f"Logged for {date_str}")
            st.rerun()

    st.divider()
    st.subheader("Weekly Activities (log each session)")
    st.caption("Tip: Use this to log strength sessions, Zone 2 minutes, and run/walk minutes. The dashboard goals will auto-update.")

    if weekly_routines:
        with st.form("weekly_activity_form"):
            options = {w["name"]: w for w in weekly_routines}
            selected_name = st.selectbox("Activity", list(options.keys()))
            selected = options[selected_name]
            wtype = selected.get("type", "count")

            if wtype == "minutes":
                val = st.number_input("Minutes", min_value=0.0, value=30.0, step=5.0)
            else:
                val = st.number_input("Count", min_value=0.0, value=1.0, step=1.0)

            notes = st.text_input("Notes (optional)", value="")
            add = st.form_submit_button("Log Activity")
            if add:
                dm.log_entry(date_str, selected["id"], val, notes=notes)
                st.success("Activity logged.")
                st.rerun()
    else:
        st.info("No weekly routines found in `data/routines.yaml`.")

# --- RESEARCH ---
with tab3:
    st.header("Research & Plans")
    
    research_dir = os.path.join(os.path.dirname(__file__), 'research')
    if os.path.exists(research_dir):
        files = []
        for root, _, filenames in os.walk(research_dir):
            for fn in filenames:
                if fn.endswith(".md"):
                    rel = os.path.relpath(os.path.join(root, fn), research_dir)
                    files.append(rel)
        files = sorted(files)
        if files:
            selected_file = st.selectbox("Select Plan", files)
            with open(os.path.join(research_dir, selected_file), 'r') as f:
                content = f.read()
                st.markdown(content)
        else:
            st.info("No research files found in `research/`")
    else:
        st.warning("Research directory missing.")


