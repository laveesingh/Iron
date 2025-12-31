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
tab1, tab2, tab3, tab4 = st.tabs(["Dashboard", "Fitness Plan", "Daily Tracker", "Research & Plans"])

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
with tab3:
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

# --- FITNESS PLAN ---
with tab2:
    st.header("Fitness Plan")

    plans_obj = dm.load_plans()
    plan = dm.get_active_plan()
    if not plan:
        st.warning("No active plan configured in `data/plans/index.yaml` (or legacy `data/plans.yaml`).")
    else:
        st.subheader(plan.get("name", plan.get("id", "Active Plan")))

        # --- Plan Editor (Full) ---
        st.caption("Plan Editor (v1): edit schedule, workouts, and rules. Every save creates an archive copy.")
        editor_tab, preview_tab = st.tabs(["Edit Plan", "Preview / Validate"])

        with preview_tab:
            errs = dm.validate_active_plan()
            if errs:
                st.error("Plan validation failed:")
                for e in errs:
                    st.write(f"- {e}")
            else:
                st.success("Plan validation OK.")

        with editor_tab:
            # Minimal-maintenance approach: basic structured editors + optional raw YAML editor
            st.subheader("Schedule")
            schedule = (plan.get("schedule") or {}).get("days") or {}
            templates = plan.get("templates") or {}
            template_ids = list(templates.keys())

            # Day mapping: Mon=0..Sun=6
            day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            new_schedule = {}
            cols = st.columns(7)
            for i in range(7):
                key = str(i)
                cfg = schedule.get(key) or {}
                primary = cfg.get("primary")
                with cols[i]:
                    st.caption(day_names[i])
                    choice = st.selectbox(
                        "Primary",
                        options=template_ids,
                        index=template_ids.index(primary) if primary in template_ids else 0,
                        key=f"schedule_primary_{i}",
                    )
                    new_schedule[key] = {"primary": choice}

            st.subheader("Targets")
            targets = plan.get("targets") or {}
            strength_target = st.number_input(
                "Strength sessions per week",
                min_value=0,
                value=int(targets.get("strength_sessions_per_week", 3)),
                step=1,
            )
            zone2_target = st.number_input(
                "Zone 2 minutes per week",
                min_value=0,
                value=int(targets.get("zone2_minutes_per_week", 90)),
                step=5,
            )
            runwalk_target = st.number_input(
                "Run/Walk minutes per week",
                min_value=0,
                value=int(targets.get("run_walk_minutes_per_week", 25)),
                step=5,
            )

            st.subheader("Adaptive Rules")
            # simple knobs (full editor iteration 1)
            knee_thr = st.number_input("Knee pain 7d avg threshold", min_value=0.0, max_value=10.0, value=3.0, step=0.5)
            sleep_thr = st.number_input("Sleep 3d avg threshold", min_value=0.0, max_value=12.0, value=6.0, step=0.5)

            if st.button("Save Plan Changes"):
                # Save back to plan spec file via data_manager
                plans_index = dm.load_plans()
                active_id = plans_index.get("active_plan_id")
                plan_file = None
                for p in plans_index.get("plans", []):
                    if p.get("id") == active_id:
                        plan_file = p.get("file")
                        break
                if not plan_file:
                    st.error("Active plan file not found in index.")
                else:
                    spec = dm.load_plan_spec(plan_file) or {}
                    spec.setdefault("targets", {})
                    spec.setdefault("schedule", {})
                    spec["schedule"]["days"] = new_schedule
                    spec["targets"]["strength_sessions_per_week"] = int(strength_target)
                    spec["targets"]["zone2_minutes_per_week"] = int(zone2_target)
                    spec["targets"]["run_walk_minutes_per_week"] = int(runwalk_target)

                    # update thresholds in known rules if present
                    rules = spec.get("adaptive_rules") or []
                    for r in rules:
                        if r.get("id") == "knee_pain_swap_run_to_zone2":
                            r.setdefault("when", {})
                            r["when"]["value"] = float(knee_thr)
                        if r.get("id") == "low_sleep_warning":
                            r.setdefault("when", {})
                            r["when"]["value"] = float(sleep_thr)
                    spec["adaptive_rules"] = rules

                    dm.save_plan_spec(plan_file, spec, archive=True)
                    st.success("Plan saved (archived previous version).")
                    st.rerun()

        # Start date (drives week number)
        try:
            start_date = pd.to_datetime(plan.get("start_date")).date()
        except Exception:
            start_date = date.today()

        colA, colB = st.columns([1, 1])
        with colA:
            new_start = st.date_input("Plan start date", start_date, key="plan_start_date")
        with colB:
            week_num = dm.get_plan_week_number(plan, today=date.today())
            st.metric("Current plan week", week_num)

        if new_start != start_date:
            if st.button("Save start date"):
                dm.set_active_plan_start_date(plan.get("id"), new_start.strftime("%Y-%m-%d"))
                st.success("Saved.")
                st.rerun()

        st.divider()

        # Show today's recommendation and provide one-click logging (PlanSpec-driven)
        rec = dm.plan_today_recommendation(date.today())
        st.subheader(rec["title"])
        for a in rec.get("actions", []):
            st.write(f"- {a}")

        for n in rec.get("notes", []):
            if (n or {}).get("level") == "warn":
                st.warning((n or {}).get("text"))
            else:
                st.info((n or {}).get("text"))

        log = rec.get("log")
        if log:
            st.caption("Log this session to count toward goals (you can edit minutes/notes).")
            minutes_default = float(log.get("default_value", 1.0))
            notes_default = str(log.get("notes", ""))

            if log["habit_id"] in ("zone2_cardio", "run_walk"):
                val = st.number_input("Minutes", min_value=0.0, value=minutes_default, step=5.0)
            else:
                val = st.number_input("Count", min_value=0.0, value=minutes_default, step=1.0)
            notes = st.text_input("Notes", value=notes_default)
            if st.button("Log today's recommended session"):
                dm.log_entry(date.today().strftime("%Y-%m-%d"), log["habit_id"], val, notes=notes)
                st.success("Logged.")
                st.rerun()

        st.divider()
        st.subheader("This Week (Plan View)")
        week = dm.plan_week_view(date.today())
        ws = week.get("week_start")
        wn = week.get("week_num")
        if ws:
            st.caption(f"Week {wn} (Mon–Sun) starting {ws.isoformat()}")

        days = week.get("days", [])
        if days:
            # quick, readable week view
            day_cols = st.columns(7)
            for i, day in enumerate(days):
                d = day.get("date")
                rec_day = (day.get("rec") or {})
                with day_cols[i]:
                    if d:
                        st.write(d.strftime("%a"))
                        st.caption(d.strftime("%m/%d"))
                    title = rec_day.get("title", "—")
                    st.write(title)

                    # completion indicator: logged if habit_id exists for that date
                    log_cfg = rec_day.get("log") or {}
                    habit_id = log_cfg.get("habit_id")
                    if d and habit_id:
                        status = dm.get_daily_status(d.strftime("%Y-%m-%d"))
                        done = habit_id in status
                        st.write("✅ Logged" if done else "⬜ Not logged")
                        if not done:
                            if st.button("Log", key=f"log_{d}_{habit_id}"):
                                default_val = float(log_cfg.get("default_value", 1))
                                notes = str(log_cfg.get("default_notes", ""))
                                dm.log_entry(d.strftime("%Y-%m-%d"), habit_id, default_val, notes=notes)
                                st.success("Logged")
                                st.rerun()
                    else:
                        st.write("—")
        else:
            st.info("No schedule days found in the active plan.")

        st.divider()
        st.subheader("Plan Document")

        research_dir = os.path.join(os.path.dirname(__file__), 'research')
        md_rel = plan.get("research_md")
        if md_rel:
            md_path = os.path.join(research_dir, md_rel)
            if os.path.exists(md_path):
                with open(md_path, "r") as f:
                    st.markdown(f.read())
            else:
                st.info(f"Plan markdown not found at `{md_rel}`.")

# --- RESEARCH ---
with tab4:
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


