# PlanSpec (Templates + Rules) — Documentation

This directory stores **versioned plan specs** for Project Iron.

## Core idea
Instead of storing a fixed calendar, a plan is stored as:
- **templates**: reusable session definitions (Strength_A, Zone2, RunWalk_Wk1_2)
- **rules**: how to schedule those templates and how to adapt based on feedback (pain/sleep)

The app generates:
- **Today view**: what to do today + how to log it
- **Week view**: recommended sessions Mon–Sun + completion indicators

## Files
- `index.yaml`: active plan pointer + available plan files
- `fitness_plan_v1.yaml`: initial plan in structured form
- `archive/`: previous versions auto-saved by the in-app editor

## PlanSpec schema (v1)

Top-level fields:
- `id`: string (unique)
- `name`: string
- `version`: string (e.g. `v1`, `v1.1`)
- `start_date`: `YYYY-MM-DD`
- `doc_md`: relative path under `project_iron/research/` to render as narrative plan doc
- `targets`: weekly targets used for dashboards and plan view
- `templates`: map of `template_id -> template`
- `schedule`: rules for which template is recommended on each weekday
- `adaptive_rules`: list of conditional rules that can swap templates or add warnings

### `targets`
Example:
- `strength_sessions_per_week`: 3
- `zone2_minutes_per_week`: 90
- `run_walk_minutes_per_week`: 25

### `templates[template_id]`
Required:
- `title`: string
- `type`: one of `strength`, `zone2`, `run_walk`, `rest`, `review`
- `log`: optional. Defines what is written to the event log when you “log this session”:
  - `habit_id`: one of the routine IDs (e.g. `strength_session`, `zone2_cardio`, `run_walk`)
  - `default_value`: number
  - `unit`: `count` or `minutes`
  - `default_notes`: string
- `steps`: ordered list of bullet strings displayed in the UI

Optional:
- `workout`: structured strength workout definition (exercise list, sets/reps/RIR)
- `progression`: rules keyed by plan week or phase

### `schedule`
Weekday mapping (Mon=0 .. Sun=6), plus optional alternative recommendations:
- `days[0].primary`: `strength_A`
- `days[0].alternatives`: `[zone2]`

### `adaptive_rules`
Each rule has:
- `id`: string
- `when`: condition:
  - `metric`: currently supports: `knee_pain_7d_avg`, `sleep_3d_avg`
  - `op`: one of `>`, `>=`, `<`, `<=`
  - `value`: number threshold
- `then`: actions:
  - `swap_template`: e.g. replace `run_walk` with `zone2`
  - `add_note`: warning text shown to user

## Design goals (why this schema)
- **Minimal maintenance**: edit a few templates + rules and the calendar generates itself.
- **Safe editing**: app validates references and required fields.
- **Versioning**: every save creates an archived copy so you can roll back.

