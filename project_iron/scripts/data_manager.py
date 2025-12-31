import yaml
import csv
import os
import pandas as pd
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
GOALS_PATH = os.path.join(DATA_DIR, 'goals.yaml')
ROUTINES_PATH = os.path.join(DATA_DIR, 'routines.yaml')
LOGS_PATH = os.path.join(DATA_DIR, 'logs', '2024-log.csv')

def load_goals():
    if not os.path.exists(GOALS_PATH):
        return []
    with open(GOALS_PATH, 'r') as f:
        data = yaml.safe_load(f)
        return data.get('goals', [])

def load_routines():
    if not os.path.exists(ROUTINES_PATH):
        return {}
    with open(ROUTINES_PATH, 'r') as f:
        data = yaml.safe_load(f)
        return data.get('routines', {})

def log_entry(date_str, habit_id, value, notes=""):
    # Ensure logs directory exists
    os.makedirs(os.path.dirname(LOGS_PATH), exist_ok=True)
    
    # Check if header needs to be written
    write_header = not os.path.exists(LOGS_PATH) or os.path.getsize(LOGS_PATH) == 0
    
    with open(LOGS_PATH, 'a', newline='') as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(['date', 'habit_id', 'value', 'notes'])
        writer.writerow([date_str, habit_id, value, notes])

def get_logs():
    if not os.path.exists(LOGS_PATH):
        return pd.DataFrame(columns=['date', 'habit_id', 'value', 'notes'])
    try:
        return pd.read_csv(LOGS_PATH)
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=['date', 'habit_id', 'value', 'notes'])

def get_daily_status(date_str):
    logs = get_logs()
    if logs.empty:
        return {}
    daily_logs = logs[logs['date'] == date_str]
    return dict(zip(daily_logs['habit_id'], daily_logs['value']))


