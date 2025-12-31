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
    
    cols = st.columns(len(goals))
    for i, goal in enumerate(goals):
        with cols[i]:
            st.subheader(goal['name'])
            st.write(f"**Target:** {goal['target']}")
            st.caption(goal['description'])
            
            for metric in goal.get('metrics', []):
                st.metric(label=metric['name'], value=f"{metric['current']} {metric['unit']}", delta=f"Target: {metric['target']}")

    st.divider()
    st.header("Recent Activity")
    logs = dm.get_logs()
    if not logs.empty:
        st.dataframe(logs.tail(10), use_container_width=True)
    else:
        st.info("No activity logged yet.")

# --- TRACKER ---
with tab2:
    st.header("Daily Tracker")
    selected_date = st.date_input("Date", date.today())
    date_str = selected_date.strftime("%Y-%m-%d")
    
    routines = dm.load_routines()
    daily_routines = routines.get('daily', [])
    
    # Get existing status for this date
    existing_status = dm.get_daily_status(date_str)
    
    with st.form("daily_log_form"):
        st.subheader("Daily Habits")
        
        form_data = {}
        for habit in daily_routines:
            # Checkbox for binary completion
            # In a real app we might want different input types based on habit type
            # keeping it simple: Checkbox = Done
            is_checked = st.checkbox(habit['name'], value=bool(existing_status.get(habit['id'])))
            form_data[habit['id']] = is_checked
            
        submitted = st.form_submit_button("Log Day")
        
        if submitted:
            for habit_id, value in form_data.items():
                # Only log if true (or handle false if we want explicit 'missed')
                # For now, let's log everything so we overwrite previous entries if needed
                # Ideally, data_manager should handle upsert. For append-only, we just append.
                dm.log_entry(date_str, habit_id, int(value))
            st.success(f"Logged for {date_str}")
            st.rerun()

# --- RESEARCH ---
with tab3:
    st.header("Research & Plans")
    
    research_dir = os.path.join(os.path.dirname(__file__), 'research')
    if os.path.exists(research_dir):
        files = [f for f in os.listdir(research_dir) if f.endswith('.md')]
        if files:
            selected_file = st.selectbox("Select Plan", files)
            with open(os.path.join(research_dir, selected_file), 'r') as f:
                content = f.read()
                st.markdown(content)
        else:
            st.info("No research files found in `research/`")
    else:
        st.warning("Research directory missing.")


