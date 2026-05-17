import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.utils.helpers import (
    now_iso,
    now_local,
    parse_iso_datetime,
    safe_float,
    safe_int,
)


class SessionEngine:
    def __init__(self, storage):
        self.storage = storage
        self.profile = storage.profile

    # ─────────────────────────────
    # ACTIVE SESSION
    # ─────────────────────────────
    def get_active(self):
        return self.profile.get("active_session")

    def _current_time(self):
        return now_local()

    def _now(self):
        return now_iso()

    def _parse_timestamp(self, value):
        return parse_iso_datetime(value) or self._current_time()

    def _build_break_plan(self, override=None):
        settings = self.profile.get("settings", {})
        plan = {
            "short_break": max(1, safe_int(settings.get("default_short_break"), 5)),
            "long_break": max(1, safe_int(settings.get("default_long_break"), 15)),
            "long_break_after": max(1, safe_int(settings.get("long_break_after"), 4)),
            "enabled": bool(settings.get("breaks_enabled", True)),
        }
        if override:
            plan.update(override)
        plan["short_break"] = max(1, safe_int(plan.get("short_break"), 5))
        plan["long_break"] = max(1, safe_int(plan.get("long_break"), 15))
        plan["long_break_after"] = max(1, safe_int(plan.get("long_break_after"), 4))
        plan["enabled"] = bool(plan.get("enabled", True))
        return plan

    def get_break_settings(self):
        plan = self._build_break_plan()
        return {
            "short_break": plan["short_break"],
            "long_break": plan["long_break"],
            "long_break_after": plan["long_break_after"],
        }

    def save_break_settings(self, short_break, long_break, long_break_after):
        settings = self.profile.setdefault("settings", {})
        settings["default_short_break"] = max(1, safe_int(short_break, 5))
        settings["default_long_break"] = max(1, safe_int(long_break, 15))
        settings["long_break_after"] = max(1, safe_int(long_break_after, 4))
        self.storage.save()
        return self.get_break_settings()

    # ─────────────────────────────
    # START FOCUS
    # ─────────────────────────────
    def start_focus(
        self,
        subject,
        minutes,
        task=None,
        task_id=None,
        tags=None,
        break_plan=None,
    ):
        minutes = safe_int(minutes, 0)
        if minutes <= 0:
            raise ValueError("Minutes must be a positive number.")

        active = self.get_active()
        if active and active.get("session_type") != "break":
            raise RuntimeError("A study session is already active.")

        cycle_count = safe_int(self.profile.get("focus_cycle_count"), 0)
        if active and active.get("session_type") == "break":
            cycle_count = max(cycle_count, safe_int(active.get("cycle_count"), 0))

        now = self._now()
        cleaned_tags = [tag.strip() for tag in (tags or []) if str(tag).strip()]

        self.profile["active_session"] = {
            "subject": (subject or "").strip() or "General",
            "planned_minutes": minutes,
            "total_seconds": minutes * 60,
            "remaining_seconds": minutes * 60,
            "state": "running",
            "started_at": now,
            "updated_at": now,
            "session_type": "focus",
            "task": (task or "").strip() or None,
            "task_title": (task or "").strip() or None,
            "task_id": safe_int(task_id, 0) or None,
            "tags": cleaned_tags,
            "distractions": [],
            "cycle_count": cycle_count,
            "break_plan": self._build_break_plan(break_plan),
        }

        self.storage.save()
        return self.profile["active_session"]

    # ─────────────────────────────
    # PAUSE / RESUME
    # ─────────────────────────────
    # TICK (CORE LOOP)
    # ─────────────────────────────
    def tick(self):
        active = self.get_active()
        if not active:
            return None

        if active.get("state") != "running":
            return active

        last = self._parse_timestamp(active.get("updated_at"))
        now = self._current_time()
        elapsed = max(0, int((now - last).total_seconds()))

        if elapsed > 0:
            active["remaining_seconds"] = max(
                0,
                safe_int(active["remaining_seconds"]) - elapsed,
            )
            active["updated_at"] = self._now()
            self.storage.save()

        return active

    # ─────────────────────────────
    # COMPLETE BREAK
    # ─────────────────────────────
    def complete_break(self, active):
        self.profile["active_session"] = None
        self.storage.save()
        return None

    # ─────────────────────────────
    # START BREAK (POMODORO LOGIC)
    # ─────────────────────────────
    def start_break(self, focus_session):
        plan = self._build_break_plan(focus_session.get("break_plan"))
        if not bool(
            self.profile.get("settings", {}).get("breaks_enabled", plan["enabled"])
        ):
            return None

        cycle = max(1, safe_int(focus_session.get("cycle_count"), 0))
        is_long = cycle % plan["long_break_after"] == 0
        minutes = plan["long_break" if is_long else "short_break"]
        now = self._now()

        self.profile["active_session"] = {
            "subject": "Long Break" if is_long else "Short Break",
            "planned_minutes": minutes,
            "total_seconds": minutes * 60,
            "remaining_seconds": minutes * 60,
            "state": "running",
            "started_at": now,
            "updated_at": now,
            "session_type": "break",
            "cycle_count": cycle,
            "tags": focus_session.get("tags", []),
            "break_plan": plan,
        }

        self.storage.save()
        return self.profile["active_session"]

    def next_break_preview(self, active=None, break_plan=None):
        active = active or self.get_active()
        override = (
            break_plan if break_plan is not None else (active or {}).get("break_plan")
        )
        plan = self._build_break_plan(override)

        if active and active.get("session_type") == "focus":
            next_cycle = safe_int(active.get("cycle_count"), 0) + 1
        else:
            next_cycle = safe_int(self.profile.get("focus_cycle_count"), 0) + 1

        is_long = next_cycle % plan["long_break_after"] == 0
        minutes = plan["long_break" if is_long else "short_break"]
        label = "Long Break" if is_long else "Short Break"
        return {
            "cycle": next_cycle,
            "minutes": minutes,
            "label": f"{label} after cycle {next_cycle}: {minutes} min",
            "is_long": is_long,
        }

    def _apply_task_progress(self, task_id, studied_minutes):
        task_id = safe_int(task_id, 0)
        if task_id <= 0:
            return

        for task in self.storage.get_collection("tasks"):
            if safe_int(task.get("id"), 0) != task_id:
                continue
            task["minutes_logged"] = round(
                safe_float(task.get("minutes_logged"), 0.0)
                + safe_float(studied_minutes),
                2,
            )
            break
