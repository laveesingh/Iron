import csv
import os
from datetime import date, datetime, timedelta

import pandas as pd
import yaml

from plan_engine import build_recommendation, build_week_view, validate_plan_spec, week_start_monday

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
GOALS_PATH = os.path.join(DATA_DIR, "goals.yaml")
ROUTINES_PATH = os.path.join(DATA_DIR, "routines.yaml")
PLANS_PATH = os.path.join(DATA_DIR, "plans.yaml")  # legacy
PLANS_DIR = os.path.join(DATA_DIR, "plans")
PLANS_INDEX_PATH = os.path.join(PLANS_DIR, "index.yaml")
LOGS_DIR = os.path.join(DATA_DIR, "logs")


def load_goals():
    if not os.path.exists(GOALS_PATH):
        return []
    with open(GOALS_PATH, "r") as f:
        data = yaml.safe_load(f)
        return data.get("goals", [])


def save_goals(goals):
    os.makedirs(os.path.dirname(GOALS_PATH), exist_ok=True)
    with open(GOALS_PATH, "w") as f:
        yaml.safe_dump({"goals": goals}, f, sort_keys=False)


def load_routines():
    if not os.path.exists(ROUTINES_PATH):
        return {}
    with open(ROUTINES_PATH, "r") as f:
        data = yaml.safe_load(f)
        return data.get("routines", {})


def load_plans():
    """
    Returns a plans index object:
      {"active_plan_id": str|None, "plans": [{"id","name","file"}...]}

    Prefers the new structure under data/plans/index.yaml.
    Falls back to legacy data/plans.yaml.
    """
    if os.path.exists(PLANS_INDEX_PATH):
        with open(PLANS_INDEX_PATH, "r") as f:
            data = yaml.safe_load(f) or {}
            return {
                "active_plan_id": data.get("active_plan_id"),
                "plans": data.get("plans", []),
            }

    # legacy fallback
    if not os.path.exists(PLANS_PATH):
        return {"active_plan_id": None, "plans": []}
    with open(PLANS_PATH, "r") as f:
        data = yaml.safe_load(f) or {}
        legacy = data.get("plans", {"active_plan_id": None, "plans": []})
        return legacy


def save_plans(plans_obj):
    """
    Saves the plans index to the new structure (data/plans/index.yaml).
    """
    os.makedirs(PLANS_DIR, exist_ok=True)
    with open(PLANS_INDEX_PATH, "w") as f:
        yaml.safe_dump(plans_obj, f, sort_keys=False)


def get_active_plan():
    plans_obj = load_plans()
    active_id = plans_obj.get("active_plan_id")
    for p in plans_obj.get("plans", []):
        if p.get("id") == active_id:
            # Resolve plan spec from file if present
            plan_file = p.get("file")
            if plan_file:
                spec = load_plan_spec(plan_file)
                # Merge index metadata over spec for display if needed
                merged = dict(spec or {})
                merged.setdefault("id", p.get("id"))
                merged.setdefault("name", p.get("name"))
                return merged
            return p
    return None


def set_active_plan_start_date(plan_id: str, start_date_str: str) -> bool:
    """
    Updates start_date inside the active plan spec YAML (not the index).
    """
    plans_obj = load_plans()
    for p in plans_obj.get("plans", []):
        if p.get("id") != plan_id:
            continue
        plan_file = p.get("file")
        if not plan_file:
            return False
        spec = load_plan_spec(plan_file) or {}
        spec["start_date"] = start_date_str
        save_plan_spec(plan_file, spec, archive=True)
        return True
    return False


def load_plan_spec(plan_file: str) -> dict | None:
    """
    plan_file is relative to data/plans/, e.g. 'fitness_plan_v1.yaml'
    """
    path = os.path.join(PLANS_DIR, plan_file)
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}


def save_plan_spec(plan_file: str, spec: dict, archive: bool = False) -> None:
    """
    Save plan spec to data/plans/<plan_file>.
    If archive=True, write a copy of the previous version to data/plans/archive/.
    """
    os.makedirs(PLANS_DIR, exist_ok=True)
    path = os.path.join(PLANS_DIR, plan_file)

    if archive and os.path.exists(path):
        os.makedirs(os.path.join(PLANS_DIR, "archive"), exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        base = os.path.splitext(os.path.basename(plan_file))[0]
        arch = os.path.join(PLANS_DIR, "archive", f"{base}.{ts}.yaml")
        with open(path, "r") as rf:
            old = rf.read()
        with open(arch, "w") as wf:
            wf.write(old)

    with open(path, "w") as f:
        yaml.safe_dump(spec, f, sort_keys=False)


def validate_active_plan() -> list[str]:
    plans_obj = load_plans()
    active_id = plans_obj.get("active_plan_id")
    if not active_id:
        return ["No active_plan_id configured."]
    for p in plans_obj.get("plans", []):
        if p.get("id") == active_id:
            plan_file = p.get("file")
            if not plan_file:
                return ["Active plan has no 'file' in index."]
            spec = load_plan_spec(plan_file)
            if not spec:
                return [f"Plan spec file not found or empty: {plan_file}"]
            return validate_plan_spec(spec)
    return ["Active plan not found in plans index."]


def get_plan_week_number(plan: dict, today: date | None = None) -> int:
    """
    Returns 1-based week number since plan start date.
    """
    today = today or date.today()
    start_str = plan.get("start_date")
    if not start_str:
        return 1
    try:
        start = _parse_date(start_str)
    except Exception:
        return 1
    if today < start:
        return 1
    delta_days = (today - start).days
    return int(delta_days // 7) + 1


def sleep_3d_avg(today: date | None = None) -> float:
    today = today or date.today()
    return avg_daily_value_over_days("sleep_hours", today, 3)


def knee_pain_7d_avg(today: date | None = None) -> float:
    today = today or date.today()
    return avg_daily_value_over_days("knee_pain", today, 7)


def plan_metrics_snapshot(today: date | None = None) -> dict[str, float]:
    today = today or date.today()
    return {
        "sleep_3d_avg": sleep_3d_avg(today),
        "knee_pain_7d_avg": knee_pain_7d_avg(today),
    }


def plan_today_recommendation(today: date | None = None) -> dict:
    today = today or date.today()
    plan = get_active_plan()
    if not plan:
        return {"title": "No active plan", "steps": [], "log": None, "notes": []}

    start_str = plan.get("start_date")
    try:
        start = _parse_date(start_str) if start_str else today
    except Exception:
        start = today

    week_num = get_plan_week_number({"start_date": start.strftime("%Y-%m-%d")}, today=today)
    metrics = plan_metrics_snapshot(today)
    rec = build_recommendation(plan, today, week_num, metrics)
    # compatibility with current UI
    return {
        "title": f"Today: {rec.get('title')}",
        "actions": rec.get("steps", []),
        "log": _normalize_log_for_ui(rec.get("log")),
        "notes": rec.get("notes", []),
    }


def plan_week_view(today: date | None = None) -> dict:
    today = today or date.today()
    plan = get_active_plan()
    if not plan:
        return {"week_start": None, "week_num": 1, "days": []}

    start_str = plan.get("start_date")
    try:
        start = _parse_date(start_str) if start_str else today
    except Exception:
        start = today

    week_num = get_plan_week_number({"start_date": start.strftime("%Y-%m-%d")}, today=today)
    ws = week_start_monday(today)
    metrics = plan_metrics_snapshot(today)
    days = build_week_view(plan, ws, week_num, metrics)
    return {"week_start": ws, "week_num": week_num, "days": days}


def _normalize_log_for_ui(log: dict | None) -> dict | None:
    if not log:
        return None
    return {
        "habit_id": log.get("habit_id"),
        "default_value": float(log.get("default_value", 1)),
        "notes": log.get("default_notes") or log.get("notes") or "",
        "unit": log.get("unit"),
    }


def _logs_path_for_date(date_str: str) -> str:
    # date_str format: YYYY-MM-DD
    year = str(date_str).split("-")[0]
    return os.path.join(LOGS_DIR, f"{year}-log.csv")


def log_entry(date_str, habit_id, value, notes=""):
    # Ensure logs directory exists
    os.makedirs(LOGS_DIR, exist_ok=True)
    logs_path = _logs_path_for_date(date_str)

    # Check if header needs to be written
    write_header = not os.path.exists(logs_path) or os.path.getsize(logs_path) == 0

    with open(logs_path, "a", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["date", "habit_id", "value", "notes"])
        writer.writerow([date_str, habit_id, value, notes])


def get_logs():
    if not os.path.exists(LOGS_DIR):
        return pd.DataFrame(columns=["date", "habit_id", "value", "notes"])

    paths = []
    for name in os.listdir(LOGS_DIR):
        if name.endswith("-log.csv"):
            paths.append(os.path.join(LOGS_DIR, name))

    if not paths:
        return pd.DataFrame(columns=["date", "habit_id", "value", "notes"])

    frames = []
    for p in sorted(paths):
        try:
            df = pd.read_csv(p)
            if not df.empty:
                frames.append(df)
        except pd.errors.EmptyDataError:
            continue

    if not frames:
        return pd.DataFrame(columns=["date", "habit_id", "value", "notes"])

    out = pd.concat(frames, ignore_index=True)
    return out


def get_daily_status(date_str):
    logs = get_logs()
    if logs.empty:
        return {}
    daily_logs = logs[logs["date"] == date_str]
    # If there are duplicates for a habit_id in the same day, last write wins.
    return dict(zip(daily_logs["habit_id"], daily_logs["value"]))


def _parse_date(date_str: str) -> date:
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def get_week_range(d: date):
    # Monday -> Sunday
    start = d - timedelta(days=d.weekday())
    end = start + timedelta(days=6)
    return start, end


def sum_habit_in_range(habit_id: str, start: date, end: date) -> float:
    logs = get_logs()
    if logs.empty:
        return 0.0
    logs = logs.copy()
    logs["date_obj"] = pd.to_datetime(logs["date"], errors="coerce").dt.date
    mask = (logs["habit_id"] == habit_id) & (logs["date_obj"] >= start) & (logs["date_obj"] <= end)
    df = logs[mask]
    if df.empty:
        return 0.0
    # Ensure numeric
    vals = pd.to_numeric(df["value"], errors="coerce").fillna(0)
    return float(vals.sum())


def avg_daily_value_over_days(habit_id: str, end_date: date, days: int) -> float:
    logs = get_logs()
    if logs.empty:
        return 0.0
    start = end_date - timedelta(days=days - 1)
    logs = logs.copy()
    logs["date_obj"] = pd.to_datetime(logs["date"], errors="coerce").dt.date
    mask = (
        (logs["habit_id"] == habit_id)
        & (logs["date_obj"] >= start)
        & (logs["date_obj"] <= end_date)
    )
    df = logs[mask]
    if df.empty:
        return 0.0
    # For daily metrics, if multiple entries exist per day, take the last one.
    df = df.sort_values(["date_obj"])
    df["value_num"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["value_num"])
    if df.empty:
        return 0.0
    daily_last = df.groupby("date_obj", as_index=False).tail(1)
    return float(daily_last["value_num"].mean())


def resolve_metric_current(metric: dict, today: date | None = None) -> float:
    today = today or date.today()
    source = metric.get("source")
    if not source:
        # fallback to stored current
        cur = metric.get("current", 0)
        try:
            return float(cur)
        except Exception:
            return 0.0

    stype = source.get("type")
    habit_id = source.get("habit_id")
    if stype == "weekly_sum" and habit_id:
        start, end = get_week_range(today)
        return sum_habit_in_range(habit_id, start, end)
    if stype == "rolling_avg_days" and habit_id:
        days = int(source.get("days", 7))
        return avg_daily_value_over_days(habit_id, today, days)

    # Unknown source type
    cur = metric.get("current", 0)
    try:
        return float(cur)
    except Exception:
        return 0.0


def update_goal_metric_current(goal_id: str, metric_name: str, new_current: float) -> bool:
    goals = load_goals()
    updated = False
    for g in goals:
        if g.get("id") != goal_id:
            continue
        for m in g.get("metrics", []):
            if m.get("name") == metric_name:
                m["current"] = float(new_current)
                updated = True
                break
    if updated:
        save_goals(goals)
    return updated
