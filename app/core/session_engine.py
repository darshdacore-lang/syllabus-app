from datetime import datetime
from app.utils.helpers import safe_int


class SessionEngine:
    def __init__(self, storage):
        self.storage = storage
        self.profile = storage.profile

    # ─────────────────────────────
    # ACTIVE SESSION
    # ─────────────────────────────
    def get_active(self):
        return self.profile.get("active_session")

    def _now(self):
        return datetime.now().isoformat()

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

    # ─────────────────────────────
    # START FOCUS
    # ─────────────────────────────
    def start_focus(self, subject, minutes, task=None, tags=None, break_plan=None):
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
    def pause(self):
        active = self.get_active()
        if active and active.get("state") == "running":
            active["state"] = "paused"
            active["updated_at"] = self._now()
            self.storage.save()

    def resume(self):
        active = self.get_active()
        if active and active.get("state") == "paused":
            active["state"] = "running"
            active["updated_at"] = self._now()
            self.storage.save()

    # ─────────────────────────────
    # MAIN TIMER TICK
    # ─────────────────────────────
    def tick(self):
        active = self.get_active()
        if not active:
            return None

        if active.get("state") != "running":
            return active

        last = datetime.fromisoformat(active.get("updated_at") or self._now())
        now = datetime.now()
        elapsed = int((now - last).total_seconds())

        if elapsed > 0:
            active["remaining_seconds"] = max(
                0,
                safe_int(active["remaining_seconds"]) - elapsed,
            )
            active["updated_at"] = now.isoformat()
            self.storage.save()

        if active["remaining_seconds"] <= 0:
            if active.get("session_type") == "focus":
                return self.complete_focus(active)
            else:
                return self.complete_break(active)

        return active

    # ─────────────────────────────
    # COMPLETE FOCUS
    # ─────────────────────────────
    def complete_focus(self, active):
        session = dict(active)
        total_seconds = max(1, safe_int(session.get("total_seconds"), 0))
        remaining_seconds = max(0, safe_int(session.get("remaining_seconds"), 0))
        completed_cycle = safe_int(session.get("cycle_count"), 0) + 1

        session["status"] = "completed"
        session["ended_at"] = self._now()
        session["cycle_count"] = completed_cycle
        session["remaining_seconds"] = remaining_seconds
        session["studied_minutes"] = round((total_seconds - remaining_seconds) / 60, 2)

        self.profile.setdefault("sessions", []).append(session)
        self.profile["active_session"] = None
        self.profile["focus_cycle_count"] = completed_cycle

        self.storage.save()

        return self.start_break(session)

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
        if not bool(self.profile.get("settings", {}).get("breaks_enabled", plan["enabled"])):
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
