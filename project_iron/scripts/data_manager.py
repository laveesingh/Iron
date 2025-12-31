import yaml
import csv
import os
import pandas as pd
from datetime import datetime, date, timedelta

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
GOALS_PATH = os.path.join(DATA_DIR, 'goals.yaml')
ROUTINES_PATH = os.path.join(DATA_DIR, 'routines.yaml')
LOGS_DIR = os.path.join(DATA_DIR, 'logs')

def load_goals():
    if not os.path.exists(GOALS_PATH):
        return []
    with open(GOALS_PATH, 'r') as f:
        data = yaml.safe_load(f)
        return data.get('goals', [])

def save_goals(goals):
    os.makedirs(os.path.dirname(GOALS_PATH), exist_ok=True)
    with open(GOALS_PATH, 'w') as f:
        yaml.safe_dump({'goals': goals}, f, sort_keys=False)

def load_routines():
    if not os.path.exists(ROUTINES_PATH):
        return {}
    with open(ROUTINES_PATH, 'r') as f:
        data = yaml.safe_load(f)
        return data.get('routines', {})

def _logs_path_for_date(date_str: str) -> str:
    # date_str format: YYYY-MM-DD
    year = str(date_str).split('-')[0]
    return os.path.join(LOGS_DIR, f'{year}-log.csv')

def log_entry(date_str, habit_id, value, notes=""):
    # Ensure logs directory exists
    os.makedirs(LOGS_DIR, exist_ok=True)
    logs_path = _logs_path_for_date(date_str)
    
    # Check if header needs to be written
    write_header = not os.path.exists(logs_path) or os.path.getsize(logs_path) == 0
    
    with open(logs_path, 'a', newline='') as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(['date', 'habit_id', 'value', 'notes'])
        writer.writerow([date_str, habit_id, value, notes])

def get_logs():
    if not os.path.exists(LOGS_DIR):
        return pd.DataFrame(columns=['date', 'habit_id', 'value', 'notes'])

    paths = []
    for name in os.listdir(LOGS_DIR):
        if name.endswith('-log.csv'):
            paths.append(os.path.join(LOGS_DIR, name))

    if not paths:
        return pd.DataFrame(columns=['date', 'habit_id', 'value', 'notes'])

    frames = []
    for p in sorted(paths):
        try:
            df = pd.read_csv(p)
            if not df.empty:
                frames.append(df)
        except pd.errors.EmptyDataError:
            continue

    if not frames:
        return pd.DataFrame(columns=['date', 'habit_id', 'value', 'notes'])

    out = pd.concat(frames, ignore_index=True)
    return out

def get_daily_status(date_str):
    logs = get_logs()
    if logs.empty:
        return {}
    daily_logs = logs[logs['date'] == date_str]
    # If there are duplicates for a habit_id in the same day, last write wins.
    return dict(zip(daily_logs['habit_id'], daily_logs['value']))

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
    logs['date_obj'] = pd.to_datetime(logs['date'], errors='coerce').dt.date
    mask = (logs['habit_id'] == habit_id) & (logs['date_obj'] >= start) & (logs['date_obj'] <= end)
    df = logs[mask]
    if df.empty:
        return 0.0
    # Ensure numeric
    vals = pd.to_numeric(df['value'], errors='coerce').fillna(0)
    return float(vals.sum())

def avg_daily_value_over_days(habit_id: str, end_date: date, days: int) -> float:
    logs = get_logs()
    if logs.empty:
        return 0.0
    start = end_date - timedelta(days=days - 1)
    logs = logs.copy()
    logs['date_obj'] = pd.to_datetime(logs['date'], errors='coerce').dt.date
    mask = (logs['habit_id'] == habit_id) & (logs['date_obj'] >= start) & (logs['date_obj'] <= end_date)
    df = logs[mask]
    if df.empty:
        return 0.0
    # For daily metrics, if multiple entries exist per day, take the last one.
    df = df.sort_values(['date_obj'])
    df['value_num'] = pd.to_numeric(df['value'], errors='coerce')
    df = df.dropna(subset=['value_num'])
    if df.empty:
        return 0.0
    daily_last = df.groupby('date_obj', as_index=False).tail(1)
    return float(daily_last['value_num'].mean())

def resolve_metric_current(metric: dict, today: date | None = None) -> float:
    today = today or date.today()
    source = metric.get('source')
    if not source:
        # fallback to stored current
        cur = metric.get('current', 0)
        try:
            return float(cur)
        except Exception:
            return 0.0

    stype = source.get('type')
    habit_id = source.get('habit_id')
    if stype == 'weekly_sum' and habit_id:
        start, end = get_week_range(today)
        return sum_habit_in_range(habit_id, start, end)
    if stype == 'rolling_avg_days' and habit_id:
        days = int(source.get('days', 7))
        return avg_daily_value_over_days(habit_id, today, days)

    # Unknown source type
    cur = metric.get('current', 0)
    try:
        return float(cur)
    except Exception:
        return 0.0

def update_goal_metric_current(goal_id: str, metric_name: str, new_current: float) -> bool:
    goals = load_goals()
    updated = False
    for g in goals:
        if g.get('id') != goal_id:
            continue
        for m in g.get('metrics', []):
            if m.get('name') == metric_name:
                m['current'] = float(new_current)
                updated = True
                break
    if updated:
        save_goals(goals)
    return updated


