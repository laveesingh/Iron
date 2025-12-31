from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any


@dataclass
class PlanNote:
    text: str
    level: str = "info"  # info | warn


def weekday_index(d: date) -> int:
    # Mon=0 .. Sun=6
    return d.weekday()


def week_start_monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def week_number_from_start(start: date, today: date) -> int:
    if today < start:
        return 1
    return (today - start).days // 7 + 1


def parse_week_range_key(key: str) -> tuple[int, int] | None:
    """
    Accepts '1-2', '3-4', or single '5'.
    """
    key = str(key).strip()
    if "-" in key:
        a, b = key.split("-", 1)
        try:
            return int(a), int(b)
        except Exception:
            return None
    try:
        n = int(key)
        return n, n
    except Exception:
        return None


def match_week_block(by_week: dict[str, Any], week_num: int) -> Any | None:
    for k, v in (by_week or {}).items():
        rng = parse_week_range_key(k)
        if not rng:
            continue
        lo, hi = rng
        if lo <= week_num <= hi:
            return v
    return None


def _compare(op: str, left: float, right: float) -> bool:
    if op == ">":
        return left > right
    if op == ">=":
        return left >= right
    if op == "<":
        return left < right
    if op == "<=":
        return left <= right
    return False


def compute_metric(metric_name: str, metrics: dict[str, float]) -> float:
    # metrics is a precomputed dict of metric -> value from logs
    return float(metrics.get(metric_name, 0.0))


def apply_adaptive_rules(
    recommended_template_id: str,
    plan_spec: dict,
    metrics: dict[str, float],
) -> tuple[str, list[PlanNote]]:
    notes: list[PlanNote] = []
    rules = plan_spec.get("adaptive_rules", []) or []
    current = recommended_template_id

    for r in rules:
        when = r.get("when") or {}
        then = r.get("then") or {}

        metric = when.get("metric")
        op = when.get("op")
        threshold = when.get("value")
        if metric is None or op is None or threshold is None:
            continue

        val = compute_metric(metric, metrics)
        try:
            thr = float(threshold)
        except Exception:
            continue

        if not _compare(str(op), val, thr):
            continue

        add_note = then.get("add_note")
        if add_note:
            notes.append(PlanNote(text=str(add_note), level="warn"))

        swap = then.get("swap_template")
        if swap and current == swap.get("from"):
            current = str(swap.get("to"))

    return current, notes


def get_template(plan_spec: dict, template_id: str) -> dict | None:
    return (plan_spec.get("templates") or {}).get(template_id)


def validate_plan_spec(spec: dict) -> list[str]:
    """
    Lightweight validation (no external schema libs).
    Returns list of human-readable errors.
    """
    errors: list[str] = []
    if not isinstance(spec, dict):
        return ["PlanSpec must be a mapping/object."]

    for k in ("id", "name", "version"):
        if not spec.get(k):
            errors.append(f"Missing required field: {k}")

    templates = spec.get("templates")
    if not isinstance(templates, dict) or not templates:
        errors.append("Missing or empty templates map.")
    else:
        for tid, tpl in templates.items():
            if not isinstance(tpl, dict):
                errors.append(f"Template '{tid}' must be a mapping.")
                continue
            if not tpl.get("title"):
                errors.append(f"Template '{tid}' missing title.")
            if not tpl.get("type"):
                errors.append(f"Template '{tid}' missing type.")
            log = tpl.get("log")
            if log is not None:
                if not isinstance(log, dict):
                    errors.append(f"Template '{tid}' log must be a mapping.")
                else:
                    if not log.get("habit_id"):
                        errors.append(f"Template '{tid}' log missing habit_id.")

    schedule = spec.get("schedule") or {}
    days = schedule.get("days")
    if not isinstance(days, dict) or not days:
        errors.append("Missing schedule.days mapping.")
    else:
        for wk, cfg in days.items():
            if not isinstance(cfg, dict):
                errors.append(f"schedule.days[{wk}] must be a mapping.")
                continue
            primary = cfg.get("primary")
            if not primary:
                errors.append(f"schedule.days[{wk}] missing primary.")
                continue
            if templates and primary not in templates:
                errors.append(f"schedule.days[{wk}] primary '{primary}' not found in templates.")
            for alt in (cfg.get("alternatives") or []):
                if templates and alt not in templates:
                    errors.append(f"schedule.days[{wk}] alternative '{alt}' not found in templates.")

    return errors


def get_recommended_template_id(plan_spec: dict, d: date) -> str | None:
    schedule = plan_spec.get("schedule") or {}
    days = schedule.get("days") or {}
    key = str(weekday_index(d))
    cfg = days.get(key) or days.get(int(key))  # allow int keys
    if not cfg:
        return None
    primary = cfg.get("primary")
    return str(primary) if primary else None


def build_recommendation(
    plan_spec: dict,
    d: date,
    week_num: int,
    metrics: dict[str, float],
) -> dict:
    """
    Returns a UI-friendly dict:
      title, steps[], template_id, log{habit_id,unit,default_value,default_notes}, notes[]
    """
    base_id = get_recommended_template_id(plan_spec, d)
    if not base_id:
        return {"title": "No recommendation", "steps": [], "template_id": None, "log": None, "notes": []}

    template_id, notes = apply_adaptive_rules(base_id, plan_spec, metrics)
    tpl = get_template(plan_spec, template_id) or {}

    steps = list(tpl.get("steps") or [])

    # Progression: run_walk has by_week prescription overrides
    if tpl.get("type") == "run_walk":
        prog = tpl.get("progression") or {}
        blk = match_week_block(prog.get("by_week") or {}, week_num)
        if blk:
            pres = blk.get("prescription")
            if pres:
                # Prepend prescription
                steps = [str(pres)] + steps
            # Override default minutes if provided
            if tpl.get("log") and blk.get("default_minutes") is not None:
                tpl = dict(tpl)
                log = dict(tpl.get("log") or {})
                log["default_value"] = blk.get("default_minutes")
                log["default_notes"] = f"Plan: {pres}" if pres else log.get("default_notes")
                tpl["log"] = log

    title = tpl.get("title") or f"Session: {template_id}"
    log = tpl.get("log")

    return {
        "template_id": template_id,
        "title": title,
        "steps": steps,
        "log": log,
        "notes": [n.__dict__ for n in notes],
        "type": tpl.get("type"),
    }


def build_week_view(plan_spec: dict, week_start: date, week_num: int, metrics: dict[str, float]) -> list[dict]:
    out = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        out.append(
            {
                "date": d,
                "weekday": i,
                "rec": build_recommendation(plan_spec, d, week_num, metrics),
            }
        )
    return out


