import json
from copy import deepcopy
from pathlib import Path


DEFAULT_GOALS = {"subject_minutes": {}}
DEFAULT_SETTINGS = {
    "breaks_enabled": True,
    "notifications_enabled": True,
    "theme": "light",
    "default_short_break": 5,
    "default_long_break": 15,
    "long_break_after": 4,
    "sound_cues": True,
}


class Storage:
    def __init__(self, path=None):
        self.path = (
            Path(path)
            if path
            else Path(__file__).resolve().parents[2] / "study_data.json"
        )
        self.data = self.load()
        self.profile = self.current_profile()

    def default_profile(self, name="Default"):
        return {
            "name": name,
            "active_session": None,
            "sessions": [],
            "tasks": [],
            "plans": [],
            "templates": [],
            "exams": [],
            "topics": [],
            "goals": deepcopy(DEFAULT_GOALS),
            "settings": deepcopy(DEFAULT_SETTINGS),
            "focus_cycle_count": 0,
            "next_task_id": 1,
            "next_plan_id": 1,
            "next_template_id": 1,
            "next_exam_id": 1,
            "next_topic_id": 1,
        }

    def default_root(self):
        default_name = "Default"
        return {
            "current_profile": default_name,
            "profiles": {default_name: self.default_profile(default_name)},
        }

    def load(self):
        if self.path.exists():
            try:
                with self.path.open("r", encoding="utf-8") as file:
                    raw = json.load(file)
            except (OSError, json.JSONDecodeError):
                raw = self.default_root()
        else:
            raw = self.default_root()

        if "profiles" not in raw or "current_profile" not in raw:
            raw = self.default_root()

        profiles = raw.get("profiles") or {}
        if not profiles:
            raw = self.default_root()
            profiles = raw["profiles"]

        migrated_profiles = {}
        for name, profile in profiles.items():
            migrated_profiles[name] = self.migrate_profile(name, profile)

        raw["profiles"] = migrated_profiles

        if raw["current_profile"] not in raw["profiles"]:
            raw["current_profile"] = next(iter(raw["profiles"]))

        return raw

    def migrate_profile(self, name, profile):
        default = self.default_profile(name)
        merged = deepcopy(default)
        merged.update(profile or {})
        merged["goals"].update((profile or {}).get("goals", {}))
        merged["settings"].update((profile or {}).get("settings", {}))

        for key in ("sessions", "tasks", "plans", "templates", "exams", "topics"):
            value = merged.get(key)
            if not isinstance(value, list):
                merged[key] = []

        return merged

    def current_profile(self):
        return self.data["profiles"][self.data["current_profile"]]

    def save(self):
        self.data["profiles"][self.data["current_profile"]] = self.profile
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(self.data, file, indent=2)

    def next_id(self, key):
        next_key = f"next_{key}_id"
        if next_key not in self.profile:
            self.profile[next_key] = 1
        value = self.profile[next_key]
        self.profile[next_key] += 1
        self.save()
        return value
