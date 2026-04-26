import csv
import json
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk


class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        widget.bind("<Enter>", self.show_tooltip)
        widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            self.tooltip,
            text=self.text,
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
        )
        label.pack()

    def hide_tooltip(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None


BASE_DIR = Path(__file__).resolve().parent
APP_NAME = "Syllabus"
DATA_FILE = BASE_DIR / "study_data.json"
CSV_EXPORT = BASE_DIR / "study_export.csv"
REPORT_EXPORT = BASE_DIR / "study_report.html"
BACKUP_FILE = BASE_DIR / "study_backup.json"
ICON_PNG = BASE_DIR / "assets" / "study-helper-icon.png"

POMODORO_PRESETS = {
    "Pomodoro 25/5": {"focus": 25, "short_break": 5, "long_break": 15, "long_after": 4},
    "Deep Work 50/10": {
        "focus": 50,
        "short_break": 10,
        "long_break": 20,
        "long_after": 3,
    },
    "Quick Sprint 15/3": {
        "focus": 15,
        "short_break": 3,
        "long_break": 10,
        "long_after": 4,
    },
    "Custom": {"focus": 30, "short_break": 5, "long_break": 15, "long_after": 4},
}
DISTRACTION_OPTIONS = [
    "Phone",
    "Noise",
    "Social Media",
    "Tired",
    "Multitasking",
    "Other",
]

LIGHT_THEME = {
    "bg": "#f4efe8",
    "card": "#fbf8f1",
    "accent": "#215145",
    "text": "#2f2a25",
    "muted": "#6a6159",
    "canvas": "#edf4ef",
    "field": "#fffdf8",
    "button": "#215145",
    "button_text": "#fbf8f1",
    "border": "#d8d0c4",
    "tab_active": "#efe6d8",
}
MIDNIGHT_THEME = {
    "bg": "#1c2329",
    "card": "#27323a",
    "accent": "#90d4c1",
    "text": "#eef5f3",
    "muted": "#b4c3bf",
    "canvas": "#223038",
    "field": "#313d46",
    "button": "#345d52",
    "button_text": "#eef5f3",
    "border": "#41525c",
    "tab_active": "#31414a",
}


def now_local():
    return datetime.now().astimezone()


def parse_iso(value):
    if not value:
        return None
    return datetime.fromisoformat(value)


def minutes_to_label(total_minutes):
    total_minutes = max(0, int(total_minutes))
    hours, minutes = divmod(total_minutes, 60)
    if hours and minutes:
        return f"{hours}h {minutes}m"
    if hours:
        return f"{hours}h"
    return f"{minutes}m"


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


class StudyStore:
    def __init__(self, path=DATA_FILE):
        self.path = Path(path)
        self.data = self.load()

    def default_profile(self, name="Default"):
        return {
            "user_name": name,
            "sessions": [],
            "tasks": [],
            "plans": [],
            "templates": [],
            "exams": [],
            "topics": [],
            "goals": {
                "daily_minutes": 120,
                "weekly_sessions": 10,
                "subject_minutes": {},
            },
            "settings": {
                "breaks_enabled": True,
                "notifications_enabled": True,
                "theme": "light",
                "default_short_break": 5,
                "default_long_break": 15,
                "long_break_after": 4,
                "sound_cues": True,
            },
            "active_session": None,
            "next_task_id": 1,
            "next_plan_id": 1,
            "next_template_id": 1,
            "next_exam_id": 1,
            "next_topic_id": 1,
        }

    def default_root(self):
        return {
            "current_profile": "Default",
            "profiles": {"Default": self.default_profile()},
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
        data = self.migrate(raw)
        self.reconcile_active_sessions(data)
        return data

    def migrate(self, raw):
        if "profiles" not in raw:
            default_name = raw.get("user_name") or "Default"
            profile = self.default_profile(default_name)
            for key in profile:
                if key in raw:
                    profile[key] = raw[key]
            raw = {"current_profile": default_name, "profiles": {default_name: profile}}

        raw.setdefault("current_profile", next(iter(raw["profiles"])))
        for name, profile in list(raw["profiles"].items()):
            raw["profiles"][name] = self.migrate_profile(name, profile)
        if raw["current_profile"] not in raw["profiles"]:
            raw["current_profile"] = next(iter(raw["profiles"]))
        return raw

    def migrate_profile(self, name, profile):
        default = self.default_profile(name)
        merged = deepcopy(default)
        merged.update(profile)
        merged["goals"].update(profile.get("goals", {}))
        merged["settings"].update(profile.get("settings", {}))

        merged["sessions"] = merged.get("sessions", [])
        merged["tasks"] = merged.get("tasks", [])
        merged["plans"] = merged.get("plans", [])
        merged["templates"] = merged.get("templates", [])
        merged["exams"] = merged.get("exams", [])
        merged["topics"] = merged.get("topics", [])

        for task in merged["tasks"]:
            task.setdefault("id", merged["next_task_id"])
            task.setdefault("title", "Untitled Task")
            task.setdefault("subject", "General")
            task.setdefault("details", "")
            task.setdefault("due_date", "")
            task.setdefault("tags", [])
            task.setdefault("status", "open")
            task.setdefault("minutes_logged", 0)
            task.setdefault("created_at", now_local().isoformat())

        for plan in merged["plans"]:
            plan.setdefault("id", merged["next_plan_id"])
            plan.setdefault("subject", "General")
            plan.setdefault("minutes", 30)
            plan.setdefault("days", [])
            plan.setdefault("time", "")
            plan.setdefault("notes", "")

        for template in merged["templates"]:
            template.setdefault("id", merged["next_template_id"])
            template.setdefault("name", "Template")
            template.setdefault("subject", "General")
            template.setdefault("minutes", 25)
            template.setdefault("tags", [])
            template.setdefault("notes", "")
            template.setdefault("preset", "Custom")

        for exam in merged["exams"]:
            exam.setdefault("id", merged["next_exam_id"])
            exam.setdefault("name", "Milestone")
            exam.setdefault("subject", "General")
            exam.setdefault("date", "")
            exam.setdefault("target_minutes", 0)
            exam.setdefault("notes", "")

        for topic in merged["topics"]:
            topic.setdefault("id", merged["next_topic_id"])
            topic.setdefault("subject", "General")
            topic.setdefault("topic", "Topic")
            topic.setdefault("progress", 0)
            topic.setdefault("notes", "")

        for session in merged["sessions"]:
            session.setdefault("task_id", None)
            session.setdefault("task_title", "")
            session.setdefault("tags", [])
            session.setdefault("note", "")
            session.setdefault("session_type", "focus")
            session.setdefault("template_name", "")
            session.setdefault("focus_score", None)
            session.setdefault("reflection", "")
            session.setdefault("next_step", "")
            session.setdefault("distractions", [])

        merged["next_task_id"] = (
            max([safe_int(t.get("id"), 0) for t in merged["tasks"]] + [0]) + 1
        )
        merged["next_plan_id"] = (
            max([safe_int(p.get("id"), 0) for p in merged["plans"]] + [0]) + 1
        )
        merged["next_template_id"] = (
            max([safe_int(t.get("id"), 0) for t in merged["templates"]] + [0]) + 1
        )
        merged["next_exam_id"] = (
            max([safe_int(e.get("id"), 0) for e in merged["exams"]] + [0]) + 1
        )
        merged["next_topic_id"] = (
            max([safe_int(t.get("id"), 0) for t in merged["topics"]] + [0]) + 1
        )
        return merged

    def current_profile(self):
        return self.data["profiles"][self.data["current_profile"]]

    def add_profile(self, name):
        name = name.strip()
        if not name or name in self.data["profiles"]:
            return False
        self.data["profiles"][name] = self.default_profile(name)
        self.data["current_profile"] = name
        self.save()
        return True

    def switch_profile(self, name):
        if name in self.data["profiles"]:
            self.data["current_profile"] = name
            self.save()

    def next_id(self, key):
        profile = self.current_profile()
        next_key = f"next_{key}_id"
        value = profile[next_key]
        profile[next_key] += 1
        return value

    def reconcile_active_sessions(self, data):
        for profile in data["profiles"].values():
            active = profile.get("active_session")
            if not active:
                continue
            remaining = safe_int(active.get("remaining_seconds"), 0)
            updated_at = parse_iso(active.get("updated_at")) or now_local()
            if active.get("state") == "running":
                elapsed = int((now_local() - updated_at).total_seconds())
                remaining = max(0, remaining - elapsed)
            active["remaining_seconds"] = remaining
            active["updated_at"] = now_local().isoformat()
            if remaining <= 0:
                self.finalize_recovered_session(profile)
            else:
                active["state"] = "paused"

    def finalize_recovered_session(self, profile):
        active = profile.get("active_session")
        if not active:
            return
        ended = now_local().isoformat()
        entry = {
            "subject": active.get("subject", "General"),
            "planned_minutes": active.get("planned_minutes", 0),
            "studied_minutes": round(safe_int(active.get("total_seconds"), 0) / 60, 1),
            "status": "completed",
            "started_at": active.get("started_at", ended),
            "ended_at": ended,
            "note": active.get("note", "")
            or "Recovered completed session from saved state.",
            "tags": active.get("tags", []),
            "task_id": active.get("task_id"),
            "task_title": active.get("task_title", ""),
            "session_type": active.get("session_type", "focus"),
            "template_name": active.get("template_name", ""),
            "focus_score": None,
            "reflection": "",
            "next_step": "",
            "distractions": active.get("distractions", []),
        }
        profile["sessions"].append(entry)
        self.apply_session_to_task(profile, entry)
        profile["active_session"] = None

    def apply_session_to_task(self, profile, session):
        if not session.get("task_id"):
            return
        for task in profile["tasks"]:
            if safe_int(task["id"]) == safe_int(session["task_id"]):
                task["minutes_logged"] = round(
                    float(task.get("minutes_logged", 0))
                    + float(session.get("studied_minutes", 0)),
                    1,
                )
                return

    def save(self):
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(self.data, file, indent=2)

    def backup(self):
        with BACKUP_FILE.open("w", encoding="utf-8") as file:
            json.dump(self.data, file, indent=2)


class StudyApp:
    def __init__(self):
        self.store = StudyStore()
        self.root = tk.Tk()
        self.app_icon = None
        self.root.title(APP_NAME)
        self.root.geometry("1400x960")
        self.root.minsize(1220, 840)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.configure_app_icon()

        self.tick_job = None
        self.notification_open = False

        # Menu bar
        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)

        file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Profile", command=self.add_profile)
        file_menu.add_command(label="Backup", command=self.create_backup)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close)

        edit_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Preferences", command=self.show_preferences)

        help_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)

        self.profile_var = tk.StringVar(value=self.store.data["current_profile"])
        self.theme_var = tk.StringVar(value=self.profile["settings"]["theme"])
        self.status_var = tk.StringVar(value="Ready.")
        self.timer_var = tk.StringVar(value="00:00")
        self.timer_subtitle_var = tk.StringVar(value="No active timer")
        self.summary_var = tk.StringVar(value="")

        self.subject_var = tk.StringVar()
        self.minutes_var = tk.StringVar(value="25")
        self.preset_var = tk.StringVar(value="Pomodoro 25/5")
        self.task_var = tk.StringVar(value="No linked task")
        self.template_var = tk.StringVar(value="No template")
        self.tags_var = tk.StringVar()
        self.breaks_var = tk.BooleanVar(
            value=self.profile["settings"]["breaks_enabled"]
        )
        self.notifications_var = tk.BooleanVar(
            value=self.profile["settings"]["notifications_enabled"]
        )
        self.sound_var = tk.BooleanVar(value=self.profile["settings"]["sound_cues"])

        self.task_title_var = tk.StringVar()
        self.task_subject_var = tk.StringVar()
        self.task_due_var = tk.StringVar()
        self.task_tags_var = tk.StringVar()
        self.task_search_var = tk.StringVar()
        self.task_filter_var = tk.StringVar(value="open")

        self.plan_subject_var = tk.StringVar()
        self.plan_minutes_var = tk.StringVar(value="30")
        self.plan_days_var = tk.StringVar()
        self.plan_time_var = tk.StringVar()

        self.exam_name_var = tk.StringVar()
        self.exam_subject_var = tk.StringVar()
        self.exam_date_var = tk.StringVar()
        self.exam_target_var = tk.StringVar(value="300")

        self.topic_subject_var = tk.StringVar()
        self.topic_name_var = tk.StringVar()
        self.topic_progress_var = tk.StringVar(value="0")

        self.template_name_var = tk.StringVar()
        self.history_search_var = tk.StringVar()
        self.history_status_var = tk.StringVar(value="all")

        self.daily_goal_var = tk.StringVar(
            value=str(self.profile["goals"]["daily_minutes"])
        )
        self.weekly_goal_var = tk.StringVar(
            value=str(self.profile["goals"]["weekly_sessions"])
        )
        self.subject_goal_var = tk.StringVar()
        self.subject_goal_minutes_var = tk.StringVar()

        self.session_note_text: tk.Text
        self.task_details_text: tk.Text
        self.plan_notes_text: tk.Text
        self.exam_notes_text: tk.Text
        self.topic_notes_text: tk.Text
        self.review_text: tk.Text
        self.dashboard_text: tk.Text
        self.history_note_text: tk.Text
        self.chart_canvas: tk.Canvas
        self.task_tree: ttk.Treeview
        self.plan_tree: ttk.Treeview
        self.exam_tree: ttk.Treeview
        self.topic_tree: ttk.Treeview
        self.history_tree: ttk.Treeview
        self.template_tree: ttk.Treeview
        self.subject_goal_tree: ttk.Treeview

        self.task_labels = {}
        self.template_labels = {}
        self.theme = LIGHT_THEME

        self.configure_style()
        self.build_ui()
        self.apply_theme()
        self.refresh_everything()
        self.restore_active_session()
        self.bind_shortcuts()

    @property
    def profile(self):
        return self.store.current_profile()

    def configure_style(self):
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")

    def configure_app_icon(self):
        # Icon loading disabled for bundled app
        pass

    def build_ui(self):
        self.main = ttk.Frame(self.root, padding=24)
        self.main.pack(fill="both", expand=True)
        self.main.columnconfigure(0, weight=3)
        self.main.columnconfigure(1, weight=2)
        self.main.rowconfigure(1, weight=1)

        self.build_header()
        self.build_left_side()
        self.build_right_side()
        self.build_status_bar()

    def build_header(self):
        self.header = ttk.Frame(self.main)
        self.header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 18))
        self.header.columnconfigure(0, weight=1)

        self.title_label = ttk.Label(
            self.header, text=APP_NAME, font=("Avenir Next", 28, "bold")
        )
        self.title_label.grid(row=0, column=0, sticky="w")
        self.subtitle_label = ttk.Label(
            self.header,
            text="Planning, focus, reflection, analytics, and growth in one study system.",
            font=("Avenir Next", 11),
        )
        self.subtitle_label.grid(row=1, column=0, sticky="w", pady=(2, 0))

        controls = ttk.Frame(self.header)
        controls.grid(row=0, column=1, rowspan=2, sticky="e")

        ttk.Label(controls, text="Profile").grid(row=0, column=0, sticky="e")
        self.profile_combo = ttk.Combobox(
            controls, textvariable=self.profile_var, state="readonly", width=16
        )
        self.profile_combo.grid(row=0, column=1, padx=6)
        self.profile_combo.bind(
            "<<ComboboxSelected>>", lambda _event: self.switch_profile()
        )
        ttk.Button(controls, text="New Profile", command=self.add_profile).grid(
            row=0, column=2, padx=4
        )

        ttk.Label(controls, text="Theme").grid(row=1, column=0, sticky="e")
        self.theme_combo = ttk.Combobox(
            controls,
            textvariable=self.theme_var,
            values=["light", "midnight"],
            state="readonly",
            width=16,
        )
        self.theme_combo.grid(row=1, column=1, padx=6)
        self.theme_combo.bind(
            "<<ComboboxSelected>>", lambda _event: self.change_theme()
        )
        ttk.Button(controls, text="Backup", command=self.create_backup).grid(
            row=1, column=2, padx=4
        )

    def build_left_side(self):
        left = ttk.Frame(self.main)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 16))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)

        self.build_timer_card(left)
        self.build_tabs(left)

    def build_right_side(self):
        right = ttk.Frame(self.main)
        right.grid(row=1, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        self.build_session_builder(right)
        self.build_planner_panel(right)

    def build_status_bar(self):
        self.status_bar = ttk.Frame(self.root, relief="sunken", padding=4)
        self.status_bar.pack(fill="x", side="bottom")
        self.status_bar_label = ttk.Label(self.status_bar, textvariable=self.status_var)
        self.status_bar_label.pack(side="left")
        self.version_label = ttk.Label(self.status_bar, text="Study Helper v1.0")
        self.version_label.pack(side="right")

    def bind_shortcuts(self):
        self.root.bind("<Control-s>", lambda e: self.start_session())
        self.root.bind("<Control-p>", lambda e: self.toggle_pause())
        self.root.bind("<Control-f>", lambda e: self.finish_now())
        self.root.bind("<Control-c>", lambda e: self.cancel_session())
        self.root.focus_set()  # Ensure the root can receive key events

    def build_timer_card(self, parent):
        self.timer_card = ttk.Frame(parent, padding=20)
        self.timer_card.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        self.timer_card.columnconfigure(0, weight=1)

        self.timer_subtitle = ttk.Label(
            self.timer_card,
            textvariable=self.timer_subtitle_var,
            font=("Avenir Next", 11),
        )
        self.timer_subtitle.grid(row=0, column=0, sticky="w")
        self.timer_label = tk.Label(
            self.timer_card,
            textvariable=self.timer_var,
            font=("Avenir Next Condensed", 42, "bold"),
        )
        self.timer_label.grid(row=1, column=0, sticky="w", pady=(4, 8))

        # Add progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.timer_card, variable=self.progress_var, maximum=100, mode="determinate"
        )
        self.progress_bar.grid(row=2, column=0, sticky="ew", pady=(0, 8))

        self.status_label = ttk.Label(
            self.timer_card,
            textvariable=self.status_var,
            font=("Avenir Next", 11),
            wraplength=720,
        )
        self.status_label.grid(row=3, column=0, sticky="w")
        self.summary_label = ttk.Label(
            self.timer_card, textvariable=self.summary_var, font=("Avenir Next", 10)
        )
        self.summary_label.grid(row=4, column=0, sticky="w", pady=(4, 0))

        controls = ttk.Frame(self.timer_card)
        controls.grid(row=5, column=0, sticky="ew", pady=(14, 0))
        for idx in range(7):
            controls.columnconfigure(idx, weight=1)

        start_btn = ttk.Button(controls, text="▶ Start", command=self.start_session)
        start_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        Tooltip(start_btn, "Start a new study session")

        pause_btn = ttk.Button(
            controls, text="⏸ Pause / Resume", command=self.toggle_pause
        )
        pause_btn.grid(row=0, column=1, sticky="ew", padx=4)
        Tooltip(pause_btn, "Pause or resume the current session")

        extend_btn = ttk.Button(controls, text="+5 Min", command=self.extend_session)
        extend_btn.grid(row=0, column=2, sticky="ew", padx=4)
        Tooltip(extend_btn, "Add 5 minutes to the current session")

        finish_btn = ttk.Button(controls, text="✓ Finish Now", command=self.finish_now)
        finish_btn.grid(row=0, column=3, sticky="ew", padx=4)
        Tooltip(finish_btn, "Finish the session early")

        skip_btn = ttk.Button(controls, text="⏭ Skip Break", command=self.skip_break)
        skip_btn.grid(row=0, column=4, sticky="ew", padx=4)
        Tooltip(skip_btn, "Skip the current break")

        distract_btn = ttk.Button(
            controls, text="🚫 Log Distraction", command=self.log_distraction
        )
        distract_btn.grid(row=0, column=5, sticky="ew", padx=4)
        Tooltip(distract_btn, "Log a distraction during the session")

        cancel_btn = ttk.Button(controls, text="✕ Cancel", command=self.cancel_session)
        cancel_btn.grid(row=0, column=6, sticky="ew", padx=(4, 0))
        Tooltip(cancel_btn, "Cancel the current session")

    def build_tabs(self, parent):
        notebook = ttk.Notebook(parent)
        notebook.grid(row=1, column=0, sticky="nsew")

        review_tab = ttk.Frame(notebook, padding=12)
        dashboard_tab = ttk.Frame(notebook, padding=12)
        tasks_tab = ttk.Frame(notebook, padding=12)
        plans_tab = ttk.Frame(notebook, padding=12)
        syllabus_tab = ttk.Frame(notebook, padding=12)
        history_tab = ttk.Frame(notebook, padding=12)
        goals_tab = ttk.Frame(notebook, padding=12)

        notebook.add(review_tab, text="📝 Daily Review")
        notebook.add(dashboard_tab, text="📊 Dashboard")
        notebook.add(tasks_tab, text="✅ Tasks")
        notebook.add(plans_tab, text="📅 Plans & Exams")
        notebook.add(syllabus_tab, text="📚 Syllabus")
        notebook.add(history_tab, text="📈 History")
        notebook.add(goals_tab, text="🎯 Goals")

        self.build_review_tab(review_tab)
        self.build_dashboard_tab(dashboard_tab)
        self.build_tasks_tab(tasks_tab)
        self.build_plans_tab(plans_tab)
        self.build_syllabus_tab(syllabus_tab)
        self.build_history_tab(history_tab)
        self.build_goals_tab(goals_tab)

    def build_review_tab(self, parent):
        ttk.Label(parent, text="Daily Review", font=("Avenir Next", 18, "bold")).pack(
            anchor="w"
        )
        self.review_text = tk.Text(
            parent, height=24, wrap="word", relief="flat", font=("Avenir Next", 11)
        )
        self.review_text.pack(fill="both", expand=True, pady=(10, 0))
        self.review_text.configure(state="disabled")

    def build_dashboard_tab(self, parent):
        ttk.Label(parent, text="Analytics", font=("Avenir Next", 18, "bold")).pack(
            anchor="w"
        )
        self.dashboard_text = tk.Text(
            parent, height=11, wrap="word", relief="flat", font=("Avenir Next", 11)
        )
        self.dashboard_text.pack(fill="x", pady=(10, 10))
        self.dashboard_text.configure(state="disabled")
        self.chart_canvas = tk.Canvas(parent, height=260, highlightthickness=0)
        self.chart_canvas.pack(fill="both", expand=True)

    def build_tasks_tab(self, parent):
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill="x")
        ttk.Label(toolbar, text="Search").pack(side="left")
        search_entry = ttk.Entry(toolbar, textvariable=self.task_search_var, width=18)
        search_entry.pack(side="left", padx=6)
        search_entry.bind("<KeyRelease>", lambda _event: self.refresh_tasks())
        ttk.Label(toolbar, text="Status").pack(side="left", padx=(8, 0))
        status_combo = ttk.Combobox(
            toolbar,
            textvariable=self.task_filter_var,
            values=["open", "done", "all"],
            state="readonly",
            width=8,
        )
        status_combo.pack(side="left", padx=6)
        status_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh_tasks())
        ttk.Button(toolbar, text="Mark Done", command=self.mark_task_done).pack(
            side="left", padx=6
        )
        ttk.Button(toolbar, text="Delete", command=self.delete_task).pack(side="left")

        columns = (
            "id",
            "title",
            "subject",
            "priority",
            "due",
            "logged",
            "tags",
            "status",
        )
        self.task_tree = ttk.Treeview(
            parent, columns=columns, show="headings", height=14
        )
        for column, title, width in [
            ("id", "ID", 50),
            ("title", "Title", 230),
            ("subject", "Subject", 120),
            ("priority", "Priority", 80),
            ("due", "Due", 100),
            ("logged", "Logged", 80),
            ("tags", "Tags", 160),
            ("status", "Status", 80),
        ]:
            self.task_tree.heading(column, text=title)
            self.task_tree.column(column, width=width, anchor="w")
        self.task_tree.pack(fill="both", expand=True, pady=(10, 0))

        ttk.Label(parent, text="Task Details").pack(anchor="w", pady=(10, 0))
        self.task_details_text = tk.Text(
            parent, height=4, wrap="word", relief="flat", font=("Avenir Next", 10)
        )
        self.task_details_text.pack(fill="x")

    def build_plans_tab(self, parent):
        top = ttk.Panedwindow(parent, orient="horizontal")
        top.pack(fill="both", expand=True)

        plan_frame = ttk.Frame(top, padding=6)
        exam_frame = ttk.Frame(top, padding=6)
        template_frame = ttk.Frame(top, padding=6)
        top.add(plan_frame, weight=2)
        top.add(exam_frame, weight=2)
        top.add(template_frame, weight=2)

        ttk.Label(
            plan_frame, text="Recurring Plans", font=("Avenir Next", 15, "bold")
        ).pack(anchor="w")
        self.plan_tree = ttk.Treeview(
            plan_frame,
            columns=("id", "subject", "minutes", "days", "time"),
            show="headings",
            height=10,
        )
        for column, title, width in [
            ("id", "ID", 45),
            ("subject", "Subject", 110),
            ("minutes", "Minutes", 80),
            ("days", "Days", 140),
            ("time", "Time", 80),
        ]:
            self.plan_tree.heading(column, text=title)
            self.plan_tree.column(column, width=width, anchor="w")
        self.plan_tree.pack(fill="both", expand=True, pady=(8, 0))
        ttk.Button(plan_frame, text="Delete Plan", command=self.delete_plan).pack(
            anchor="e", pady=(8, 0)
        )

        ttk.Label(
            exam_frame, text="Exams & Milestones", font=("Avenir Next", 15, "bold")
        ).pack(anchor="w")
        self.exam_tree = ttk.Treeview(
            exam_frame,
            columns=("id", "name", "subject", "date", "target"),
            show="headings",
            height=10,
        )
        for column, title, width in [
            ("id", "ID", 45),
            ("name", "Name", 140),
            ("subject", "Subject", 100),
            ("date", "Date", 100),
            ("target", "Target", 90),
        ]:
            self.exam_tree.heading(column, text=title)
            self.exam_tree.column(column, width=width, anchor="w")
        self.exam_tree.pack(fill="both", expand=True, pady=(8, 0))
        ttk.Button(exam_frame, text="Delete Exam", command=self.delete_exam).pack(
            anchor="e", pady=(8, 0)
        )

        ttk.Label(
            template_frame, text="Session Templates", font=("Avenir Next", 15, "bold")
        ).pack(anchor="w")
        self.template_tree = ttk.Treeview(
            template_frame,
            columns=("id", "name", "subject", "minutes", "preset", "tags"),
            show="headings",
            height=10,
        )
        for column, title, width in [
            ("id", "ID", 45),
            ("name", "Name", 120),
            ("subject", "Subject", 100),
            ("minutes", "Minutes", 80),
            ("preset", "Preset", 120),
            ("tags", "Tags", 150),
        ]:
            self.template_tree.heading(column, text=title)
            self.template_tree.column(column, width=width, anchor="w")
        self.template_tree.pack(fill="both", expand=True, pady=(8, 0))
        self.template_tree.bind(
            "<<TreeviewSelect>>", lambda _event: self.apply_template_from_tree()
        )
        ttk.Button(
            template_frame, text="Delete Template", command=self.delete_template
        ).pack(anchor="e", pady=(8, 0))

    def build_syllabus_tab(self, parent):
        ttk.Label(
            parent, text="Syllabus Tracker", font=("Avenir Next", 18, "bold")
        ).pack(anchor="w")
        self.topic_tree = ttk.Treeview(
            parent,
            columns=("id", "subject", "topic", "progress"),
            show="headings",
            height=14,
        )
        for column, title, width in [
            ("id", "ID", 45),
            ("subject", "Subject", 140),
            ("topic", "Topic", 260),
            ("progress", "Progress", 90),
        ]:
            self.topic_tree.heading(column, text=title)
            self.topic_tree.column(column, width=width, anchor="w")
        self.topic_tree.pack(fill="both", expand=True, pady=(10, 0))
        controls = ttk.Frame(parent)
        controls.pack(fill="x", pady=(8, 0))
        ttk.Button(
            controls,
            text="Increase +10%",
            command=lambda: self.shift_topic_progress(10),
        ).pack(side="left")
        ttk.Button(
            controls,
            text="Decrease -10%",
            command=lambda: self.shift_topic_progress(-10),
        ).pack(side="left", padx=6)
        ttk.Button(controls, text="Delete Topic", command=self.delete_topic).pack(
            side="left"
        )

    def build_history_tab(self, parent):
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill="x")
        ttk.Label(toolbar, text="Search").pack(side="left")
        history_entry = ttk.Entry(
            toolbar, textvariable=self.history_search_var, width=18
        )
        history_entry.pack(side="left", padx=6)
        history_entry.bind("<KeyRelease>", lambda _event: self.refresh_history())
        ttk.Label(toolbar, text="Status").pack(side="left", padx=(8, 0))
        history_status = ttk.Combobox(
            toolbar,
            textvariable=self.history_status_var,
            values=["all", "completed", "cancelled"],
            state="readonly",
            width=10,
        )
        history_status.pack(side="left", padx=6)
        history_status.bind(
            "<<ComboboxSelected>>", lambda _event: self.refresh_history()
        )
        ttk.Button(toolbar, text="Export CSV", command=self.export_csv).pack(
            side="left", padx=6
        )
        ttk.Button(toolbar, text="Export Report", command=self.export_report).pack(
            side="left"
        )

        columns = ("ended", "subject", "task", "minutes", "score", "status", "tags")
        self.history_tree = ttk.Treeview(
            parent, columns=columns, show="headings", height=12
        )
        for column, title, width in [
            ("ended", "Ended", 140),
            ("subject", "Subject", 120),
            ("task", "Task", 150),
            ("minutes", "Minutes", 80),
            ("score", "Focus", 70),
            ("status", "Status", 90),
            ("tags", "Tags", 180),
        ]:
            self.history_tree.heading(column, text=title)
            self.history_tree.column(column, width=width, anchor="w")
        self.history_tree.pack(fill="both", expand=True, pady=(10, 10))
        self.history_tree.bind(
            "<<TreeviewSelect>>", lambda _event: self.show_history_note()
        )

        self.history_note_text = tk.Text(
            parent, height=8, wrap="word", relief="flat", font=("Avenir Next", 11)
        )
        self.history_note_text.pack(fill="x")
        self.history_note_text.insert(
            "1.0", "Select a session to review notes, reflection, and next steps."
        )
        self.history_note_text.configure(state="disabled")

    def build_goals_tab(self, parent):
        top = ttk.Frame(parent)
        top.pack(fill="x")
        ttk.Label(top, text="Daily Minutes").grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.daily_goal_var, width=10).grid(
            row=0, column=1, padx=6
        )
        ttk.Label(top, text="Weekly Sessions").grid(
            row=0, column=2, sticky="w", padx=(12, 0)
        )
        ttk.Entry(top, textvariable=self.weekly_goal_var, width=10).grid(
            row=0, column=3, padx=6
        )
        ttk.Checkbutton(top, text="Auto Breaks", variable=self.breaks_var).grid(
            row=1, column=0, sticky="w", pady=(8, 0)
        )
        ttk.Checkbutton(
            top, text="Notifications", variable=self.notifications_var
        ).grid(row=1, column=1, sticky="w", pady=(8, 0))
        ttk.Checkbutton(top, text="Sound Cues", variable=self.sound_var).grid(
            row=1, column=2, sticky="w", pady=(8, 0)
        )
        ttk.Button(top, text="Save Settings", command=self.save_settings).grid(
            row=1, column=3, sticky="e", pady=(8, 0)
        )

        subject_goal_form = ttk.Frame(parent)
        subject_goal_form.pack(fill="x", pady=(14, 10))
        ttk.Label(subject_goal_form, text="Subject Goal").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Entry(subject_goal_form, textvariable=self.subject_goal_var, width=18).grid(
            row=0, column=1, padx=6
        )
        ttk.Label(subject_goal_form, text="Weekly Minutes").grid(
            row=0, column=2, sticky="w"
        )
        ttk.Entry(
            subject_goal_form, textvariable=self.subject_goal_minutes_var, width=10
        ).grid(row=0, column=3, padx=6)
        ttk.Button(
            subject_goal_form, text="Add / Update", command=self.add_subject_goal
        ).grid(row=0, column=4, padx=6)
        ttk.Button(
            subject_goal_form, text="Delete", command=self.delete_subject_goal
        ).grid(row=0, column=5)

        self.subject_goal_tree = ttk.Treeview(
            parent, columns=("subject", "goal", "progress"), show="headings", height=12
        )
        for column, title, width in [
            ("subject", "Subject", 180),
            ("goal", "Goal", 100),
            ("progress", "Progress", 140),
        ]:
            self.subject_goal_tree.heading(column, text=title)
            self.subject_goal_tree.column(column, width=width, anchor="w")
        self.subject_goal_tree.pack(fill="both", expand=True)

    def build_session_builder(self, parent):
        self.session_panel = ttk.LabelFrame(parent, text="Session Builder", padding=14)
        self.session_panel.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        for idx in range(2):
            self.session_panel.columnconfigure(idx, weight=1)

        ttk.Label(self.session_panel, text="Subject").grid(row=0, column=0, sticky="w")
        ttk.Entry(self.session_panel, textvariable=self.subject_var).grid(
            row=1, column=0, sticky="ew", padx=(0, 8)
        )
        ttk.Label(self.session_panel, text="Minutes").grid(row=0, column=1, sticky="w")
        ttk.Entry(self.session_panel, textvariable=self.minutes_var).grid(
            row=1, column=1, sticky="ew"
        )

        ttk.Label(self.session_panel, text="Preset").grid(
            row=2, column=0, sticky="w", pady=(10, 0)
        )
        preset_combo = ttk.Combobox(
            self.session_panel,
            textvariable=self.preset_var,
            values=list(POMODORO_PRESETS.keys()),
            state="readonly",
        )
        preset_combo.grid(row=3, column=0, sticky="ew", padx=(0, 8))
        preset_combo.bind("<<ComboboxSelected>>", lambda _event: self.select_preset())
        ttk.Label(self.session_panel, text="Linked Task").grid(
            row=2, column=1, sticky="w", pady=(10, 0)
        )
        self.task_combo = ttk.Combobox(
            self.session_panel, textvariable=self.task_var, state="readonly"
        )
        self.task_combo.grid(row=3, column=1, sticky="ew")

        ttk.Label(self.session_panel, text="Template").grid(
            row=4, column=0, sticky="w", pady=(10, 0)
        )
        self.template_combo = ttk.Combobox(
            self.session_panel, textvariable=self.template_var, state="readonly"
        )
        self.template_combo.grid(row=5, column=0, sticky="ew", padx=(0, 8))
        self.template_combo.bind(
            "<<ComboboxSelected>>", lambda _event: self.apply_template_choice()
        )
        ttk.Button(
            self.session_panel, text="Save Template", command=self.save_template
        ).grid(row=5, column=1, sticky="ew")

        ttk.Label(self.session_panel, text="Tags").grid(
            row=6, column=0, sticky="w", pady=(10, 0)
        )
        ttk.Entry(self.session_panel, textvariable=self.tags_var).grid(
            row=7, column=0, sticky="ew", padx=(0, 8)
        )
        ttk.Label(self.session_panel, text="Notes").grid(
            row=6, column=1, sticky="w", pady=(10, 0)
        )
        self.session_note_text = tk.Text(
            self.session_panel,
            height=5,
            wrap="word",
            relief="flat",
            font=("Avenir Next", 10),
        )
        self.session_note_text.grid(row=7, column=1, sticky="ew")

    def build_planner_panel(self, parent):
        notebook = ttk.Notebook(parent)
        notebook.grid(row=1, column=0, sticky="nsew")

        plan_builder = ttk.Frame(notebook, padding=12)
        exam_builder = ttk.Frame(notebook, padding=12)
        topic_builder = ttk.Frame(notebook, padding=12)
        notebook.add(plan_builder, text="Plan Builder")
        notebook.add(exam_builder, text="Exam Builder")
        notebook.add(topic_builder, text="Topic Builder")

        ttk.Label(plan_builder, text="Subject").grid(row=0, column=0, sticky="w")
        ttk.Entry(plan_builder, textvariable=self.plan_subject_var).grid(
            row=1, column=0, sticky="ew", padx=(0, 8)
        )
        ttk.Label(plan_builder, text="Minutes").grid(row=0, column=1, sticky="w")
        ttk.Entry(plan_builder, textvariable=self.plan_minutes_var).grid(
            row=1, column=1, sticky="ew"
        )
        ttk.Label(plan_builder, text="Days (Mon,Tue)").grid(
            row=2, column=0, sticky="w", pady=(10, 0)
        )
        ttk.Entry(plan_builder, textvariable=self.plan_days_var).grid(
            row=3, column=0, sticky="ew", padx=(0, 8)
        )
        ttk.Label(plan_builder, text="Time").grid(
            row=2, column=1, sticky="w", pady=(10, 0)
        )
        ttk.Entry(plan_builder, textvariable=self.plan_time_var).grid(
            row=3, column=1, sticky="ew"
        )
        ttk.Label(plan_builder, text="Notes").grid(
            row=4, column=0, sticky="w", pady=(10, 0)
        )
        self.plan_notes_text = tk.Text(
            plan_builder, height=6, wrap="word", relief="flat", font=("Avenir Next", 10)
        )
        self.plan_notes_text.grid(row=5, column=0, columnspan=2, sticky="ew")
        ttk.Button(plan_builder, text="Add Plan", command=self.add_plan).grid(
            row=6, column=1, sticky="e", pady=(10, 0)
        )

        ttk.Label(exam_builder, text="Name").grid(row=0, column=0, sticky="w")
        ttk.Entry(exam_builder, textvariable=self.exam_name_var).grid(
            row=1, column=0, sticky="ew", padx=(0, 8)
        )
        ttk.Label(exam_builder, text="Subject").grid(row=0, column=1, sticky="w")
        ttk.Entry(exam_builder, textvariable=self.exam_subject_var).grid(
            row=1, column=1, sticky="ew"
        )
        ttk.Label(exam_builder, text="Date (YYYY-MM-DD)").grid(
            row=2, column=0, sticky="w", pady=(10, 0)
        )
        ttk.Entry(exam_builder, textvariable=self.exam_date_var).grid(
            row=3, column=0, sticky="ew", padx=(0, 8)
        )
        ttk.Label(exam_builder, text="Target Minutes").grid(
            row=2, column=1, sticky="w", pady=(10, 0)
        )
        ttk.Entry(exam_builder, textvariable=self.exam_target_var).grid(
            row=3, column=1, sticky="ew"
        )
        ttk.Label(exam_builder, text="Notes").grid(
            row=4, column=0, sticky="w", pady=(10, 0)
        )
        self.exam_notes_text = tk.Text(
            exam_builder, height=6, wrap="word", relief="flat", font=("Avenir Next", 10)
        )
        self.exam_notes_text.grid(row=5, column=0, columnspan=2, sticky="ew")
        ttk.Button(exam_builder, text="Add Exam", command=self.add_exam).grid(
            row=6, column=1, sticky="e", pady=(10, 0)
        )

        ttk.Label(topic_builder, text="Subject").grid(row=0, column=0, sticky="w")
        ttk.Entry(topic_builder, textvariable=self.topic_subject_var).grid(
            row=1, column=0, sticky="ew", padx=(0, 8)
        )
        ttk.Label(topic_builder, text="Topic").grid(row=0, column=1, sticky="w")
        ttk.Entry(topic_builder, textvariable=self.topic_name_var).grid(
            row=1, column=1, sticky="ew"
        )
        ttk.Label(topic_builder, text="Progress %").grid(
            row=2, column=0, sticky="w", pady=(10, 0)
        )
        ttk.Entry(topic_builder, textvariable=self.topic_progress_var).grid(
            row=3, column=0, sticky="ew", padx=(0, 8)
        )
        ttk.Label(topic_builder, text="Notes").grid(
            row=4, column=0, sticky="w", pady=(10, 0)
        )
        self.topic_notes_text = tk.Text(
            topic_builder,
            height=6,
            wrap="word",
            relief="flat",
            font=("Avenir Next", 10),
        )
        self.topic_notes_text.grid(row=5, column=0, columnspan=2, sticky="ew")
        ttk.Button(topic_builder, text="Add Topic", command=self.add_topic).grid(
            row=6, column=1, sticky="e", pady=(10, 0)
        )

    def apply_theme(self):
        self.theme = LIGHT_THEME if self.theme_var.get() == "light" else MIDNIGHT_THEME
        style = ttk.Style(self.root)
        style.configure(".", background=self.theme["bg"], foreground=self.theme["text"])
        style.configure("TFrame", background=self.theme["bg"])
        style.configure(
            "TLabel", background=self.theme["bg"], foreground=self.theme["text"]
        )
        style.configure(
            "TLabelframe", background=self.theme["card"], foreground=self.theme["text"]
        )
        style.configure(
            "TLabelframe.Label",
            background=self.theme["card"],
            foreground=self.theme["accent"],
        )
        style.configure("TNotebook", background=self.theme["bg"])
        style.configure(
            "TNotebook.Tab",
            background=self.theme["card"],
            foreground=self.theme["text"],
            padding=(12, 8),
        )
        style.configure(
            "TButton",
            background=self.theme["button"],
            foreground=self.theme["button_text"],
            bordercolor=self.theme["border"],
            lightcolor=self.theme["button"],
            darkcolor=self.theme["button"],
            focusthickness=1,
            focuscolor=self.theme["accent"],
        )
        style.map(
            "TButton",
            background=[
                ("active", self.theme["accent"]),
                ("pressed", self.theme["accent"]),
            ],
            foreground=[("active", self.theme["bg"]), ("pressed", self.theme["bg"])],
        )
        style.configure(
            "TEntry",
            fieldbackground=self.theme["field"],
            foreground=self.theme["text"],
            insertcolor=self.theme["text"],
            bordercolor=self.theme["border"],
            lightcolor=self.theme["border"],
            darkcolor=self.theme["border"],
        )
        style.configure(
            "TCombobox",
            fieldbackground=self.theme["field"],
            background=self.theme["field"],
            foreground=self.theme["text"],
            arrowcolor=self.theme["text"],
            bordercolor=self.theme["border"],
            lightcolor=self.theme["border"],
            darkcolor=self.theme["border"],
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", self.theme["field"])],
            foreground=[("readonly", self.theme["text"])],
            background=[("readonly", self.theme["field"])],
            selectbackground=[("readonly", self.theme["field"])],
            selectforeground=[("readonly", self.theme["text"])],
        )
        style.configure(
            "TCheckbutton",
            background=self.theme["bg"],
            foreground=self.theme["text"],
            indicatorcolor=self.theme["field"],
            indicatordiameter=14,
        )
        style.map(
            "TCheckbutton",
            background=[("active", self.theme["bg"])],
            foreground=[("active", self.theme["accent"])],
            indicatorcolor=[
                ("selected", self.theme["accent"]),
                ("!selected", self.theme["field"]),
            ],
        )
        style.configure(
            "Treeview",
            background=self.theme["card"],
            fieldbackground=self.theme["card"],
            foreground=self.theme["text"],
            rowheight=26,
            bordercolor=self.theme["border"],
            lightcolor=self.theme["border"],
            darkcolor=self.theme["border"],
        )
        style.map(
            "Treeview",
            background=[("selected", self.theme["accent"])],
            foreground=[("selected", self.theme["bg"])],
        )
        style.configure(
            "Treeview.Heading",
            background=self.theme["bg"],
            foreground=self.theme["text"],
        )
        style.configure("TPanedwindow", background=self.theme["bg"])
        style.configure("SCard.TFrame", background=self.theme["card"])
        style.configure(
            "SCard.TLabel", background=self.theme["card"], foreground=self.theme["text"]
        )
        style.map(
            "TNotebook.Tab",
            background=[
                ("selected", self.theme["tab_active"]),
                ("active", self.theme["card"]),
            ],
            foreground=[("selected", self.theme["text"])],
        )

        self.root.configure(bg=self.theme["bg"])
        for widget in [self.timer_card, self.main, self.header]:
            widget.configure(style="TFrame")
        self.session_panel.configure(style="TLabelframe")

        self.timer_label.configure(bg=self.theme["card"], fg=self.theme["accent"])
        self.chart_canvas.configure(bg=self.theme["canvas"])
        for text_widget in [
            self.dashboard_text,
            self.review_text,
            self.history_note_text,
            self.session_note_text,
            self.task_details_text,
            self.plan_notes_text,
            self.exam_notes_text,
            self.topic_notes_text,
        ]:
            if text_widget is not None:
                text_widget.configure(
                    bg=self.theme["card"],
                    fg=self.theme["text"],
                    insertbackground=self.theme["text"],
                )

        self.paint_surface_widgets(self.root)

    def paint_surface_widgets(self, widget):
        for child in widget.winfo_children():
            widget_class = child.winfo_class()
            if isinstance(child, tk.Text):
                child.configure(
                    bg=self.theme["card"],
                    fg=self.theme["text"],
                    insertbackground=self.theme["text"],
                    highlightbackground=self.theme["border"],
                    highlightcolor=self.theme["accent"],
                )
            elif isinstance(child, tk.Canvas):
                child.configure(
                    bg=self.theme["canvas"], highlightbackground=self.theme["border"]
                )
            elif widget_class in {"TFrame", "TLabelframe", "TNotebook"}:
                try:
                    child.configure(
                        style=(
                            "SCard.TFrame"
                            if child is not self.main and child is not self.header
                            else "TFrame"
                        )
                    )
                except tk.TclError:
                    pass
            elif widget_class == "TLabel":
                try:
                    parent_class = child.master.winfo_class()
                    child.configure(
                        style=(
                            "SCard.TLabel"
                            if parent_class in {"TLabelframe", "TFrame", "TNotebook"}
                            and child.master not in {self.header, self.main}
                            else "TLabel"
                        )
                    )
                except tk.TclError:
                    pass
            self.paint_surface_widgets(child)

    def change_theme(self):
        self.profile["settings"]["theme"] = self.theme_var.get()
        self.store.save()
        self.apply_theme()
        self.refresh_dashboard()
        self.refresh_review()

    def create_backup(self):
        self.store.backup()
        self.status_var.set(f"Backup created at {BACKUP_FILE.name}.")
        self.notify("Backup created", f"Saved a backup to {BACKUP_FILE.name}.")

    def switch_profile(self):
        self.store.switch_profile(self.profile_var.get())
        self.theme_var.set(self.profile["settings"]["theme"])
        self.breaks_var.set(self.profile["settings"]["breaks_enabled"])
        self.notifications_var.set(self.profile["settings"]["notifications_enabled"])
        self.sound_var.set(self.profile["settings"]["sound_cues"])
        self.daily_goal_var.set(str(self.profile["goals"]["daily_minutes"]))
        self.weekly_goal_var.set(str(self.profile["goals"]["weekly_sessions"]))
        self.refresh_everything()
        self.restore_active_session()

    def add_profile(self):
        name = simpledialog.askstring("New profile", "Profile name:", parent=self.root)
        if not name:
            return
        if not self.store.add_profile(name):
            messagebox.showerror(
                "Cannot add profile", "That profile already exists or is invalid."
            )
            return
        self.profile_var.set(name)
        self.switch_profile()

    def select_preset(self):
        preset = POMODORO_PRESETS[self.preset_var.get()]
        self.minutes_var.set(str(preset["focus"]))
        self.status_var.set(
            f"Preset selected: {self.preset_var.get()} with {preset['focus']} minutes focus time."
        )

    def parse_tags(self, text):
        return [item.strip() for item in text.split(",") if item.strip()]

    def task_options(self):
        mapping: dict[str, int | None] = {"No linked task": None}
        for task in self.sorted_tasks():
            if task["status"] == "open":
                label = f"{task['title']} [{task['subject']}]"
                mapping[label] = safe_int(task["id"])
        return mapping

    def template_options(self):
        mapping: dict[str, int | None] = {"No template": None}
        for template in self.profile["templates"]:
            mapping[template["name"]] = safe_int(template["id"])
        return mapping

    def refresh_everything(self):
        self.profile_combo["values"] = sorted(self.store.data["profiles"].keys())
        self.task_labels = self.task_options()
        self.task_combo["values"] = list(self.task_labels.keys())
        if self.task_var.get() not in self.task_labels:
            self.task_var.set("No linked task")

        self.template_labels = self.template_options()
        self.template_combo["values"] = list(self.template_labels.keys())
        if self.template_var.get() not in self.template_labels:
            self.template_var.set("No template")

        self.refresh_tasks()
        self.refresh_plans()
        self.refresh_exams()
        self.refresh_topics()
        self.refresh_history()
        self.refresh_subject_goals()
        self.refresh_dashboard()
        self.refresh_review()
        self.update_timer_display()

    def sorted_tasks(self):
        tasks = list(self.profile["tasks"])
        filtered = []
        query = self.task_search_var.get().strip().lower()
        status = self.task_filter_var.get()
        for task in tasks:
            if status != "all" and task["status"] != status:
                continue
            haystack = " ".join(
                [
                    task["title"],
                    task["subject"],
                    task.get("details", ""),
                    " ".join(task.get("tags", [])),
                ]
            ).lower()
            if query and query not in haystack:
                continue
            filtered.append(task)
        return sorted(
            filtered,
            key=lambda task: (
                -self.priority_score(task),
                task.get("due_date") or "9999-12-31",
                task["title"],
            ),
        )

    def priority_score(self, task):
        score = 0
        due = (
            parse_iso(f"{task['due_date']}T00:00:00+00:00")
            if task.get("due_date")
            else None
        )
        if due:
            days = (due.date() - now_local().date()).days
            score += (
                50
                if days < 0
                else 40 if days == 0 else 30 if days <= 2 else 15 if days <= 7 else 5
            )
        score += (
            10 if task.get("subject") in self.profile["goals"]["subject_minutes"] else 0
        )
        score += 5 if task.get("minutes_logged", 0) < 30 else 0
        return score

    def add_task(self):
        title = self.task_title_var.get().strip()
        if not title:
            messagebox.showerror("Missing title", "Task title is required.")
            return
        due = self.task_due_var.get().strip()
        if due:
            try:
                datetime.strptime(due, "%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Invalid date", "Use YYYY-MM-DD.")
                return
        task = {
            "id": self.store.next_id("task"),
            "title": title,
            "subject": self.task_subject_var.get().strip() or "General",
            "details": self.task_details_text.get("1.0", "end").strip(),
            "due_date": due,
            "tags": self.parse_tags(self.task_tags_var.get()),
            "status": "open",
            "minutes_logged": 0,
            "created_at": now_local().isoformat(),
        }
        self.profile["tasks"].append(task)
        self.store.save()
        self.task_title_var.set("")
        self.task_subject_var.set("")
        self.task_due_var.set("")
        self.task_tags_var.set("")
        self.task_details_text.delete("1.0", "end")
        self.status_var.set(f"Task added: {title}")
        self.refresh_everything()

    def selected_tree_id(self, tree):
        selected = tree.selection()
        if not selected:
            return None
        values = tree.item(selected[0], "values")
        return safe_int(values[0]) if values else None

    def mark_task_done(self):
        task_id = self.selected_tree_id(self.task_tree)
        if task_id is None:
            return
        for task in self.profile["tasks"]:
            if safe_int(task["id"]) == task_id:
                task["status"] = "done"
                break
        self.store.save()
        self.refresh_everything()

    def delete_task(self):
        task_id = self.selected_tree_id(self.task_tree)
        if task_id is None:
            return
        self.profile["tasks"] = [
            task for task in self.profile["tasks"] if safe_int(task["id"]) != task_id
        ]
        active = self.profile.get("active_session")
        if active and safe_int(active.get("task_id")) == task_id:
            active["task_id"] = None
            active["task_title"] = ""
        self.store.save()
        self.refresh_everything()

    def refresh_tasks(self):
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)
        for task in self.sorted_tasks():
            self.task_tree.insert(
                "",
                "end",
                values=(
                    task["id"],
                    task["title"],
                    task["subject"],
                    self.priority_score(task),
                    task.get("due_date", ""),
                    task.get("minutes_logged", 0),
                    ", ".join(task.get("tags", [])),
                    task["status"],
                ),
            )

    def add_plan(self):
        subject = self.plan_subject_var.get().strip()
        minutes = safe_int(self.plan_minutes_var.get(), 0)
        if not subject or minutes <= 0:
            messagebox.showerror(
                "Invalid plan", "Enter a subject and positive minutes."
            )
            return
        days = [
            day.strip() for day in self.plan_days_var.get().split(",") if day.strip()
        ]
        plan = {
            "id": self.store.next_id("plan"),
            "subject": subject,
            "minutes": minutes,
            "days": days,
            "time": self.plan_time_var.get().strip(),
            "notes": self.plan_notes_text.get("1.0", "end").strip(),
        }
        self.profile["plans"].append(plan)
        self.store.save()
        self.plan_subject_var.set("")
        self.plan_minutes_var.set("30")
        self.plan_days_var.set("")
        self.plan_time_var.set("")
        self.plan_notes_text.delete("1.0", "end")
        self.status_var.set(f"Recurring plan added for {subject}.")
        self.refresh_everything()

    def delete_plan(self):
        plan_id = self.selected_tree_id(self.plan_tree)
        if plan_id is None:
            return
        self.profile["plans"] = [
            plan for plan in self.profile["plans"] if safe_int(plan["id"]) != plan_id
        ]
        self.store.save()
        self.refresh_everything()

    def refresh_plans(self):
        for item in self.plan_tree.get_children():
            self.plan_tree.delete(item)
        for plan in self.profile["plans"]:
            self.plan_tree.insert(
                "",
                "end",
                values=(
                    plan["id"],
                    plan["subject"],
                    plan["minutes"],
                    ", ".join(plan["days"]),
                    plan["time"],
                ),
            )

    def add_exam(self):
        name = self.exam_name_var.get().strip()
        subject = self.exam_subject_var.get().strip() or "General"
        date_text = self.exam_date_var.get().strip()
        if not name or not date_text:
            messagebox.showerror("Invalid exam", "Exam name and date are required.")
            return
        try:
            datetime.strptime(date_text, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Invalid date", "Use YYYY-MM-DD.")
            return
        exam = {
            "id": self.store.next_id("exam"),
            "name": name,
            "subject": subject,
            "date": date_text,
            "target_minutes": safe_int(self.exam_target_var.get(), 0),
            "notes": self.exam_notes_text.get("1.0", "end").strip(),
        }
        self.profile["exams"].append(exam)
        self.store.save()
        self.exam_name_var.set("")
        self.exam_subject_var.set("")
        self.exam_date_var.set("")
        self.exam_target_var.set("300")
        self.exam_notes_text.delete("1.0", "end")
        self.refresh_everything()

    def delete_exam(self):
        exam_id = self.selected_tree_id(self.exam_tree)
        if exam_id is None:
            return
        self.profile["exams"] = [
            exam for exam in self.profile["exams"] if safe_int(exam["id"]) != exam_id
        ]
        self.store.save()
        self.refresh_everything()

    def refresh_exams(self):
        for item in self.exam_tree.get_children():
            self.exam_tree.delete(item)
        for exam in sorted(
            self.profile["exams"], key=lambda exam: exam["date"] or "9999-12-31"
        ):
            self.exam_tree.insert(
                "",
                "end",
                values=(
                    exam["id"],
                    exam["name"],
                    exam["subject"],
                    exam["date"],
                    exam.get("target_minutes", 0),
                ),
            )

    def add_topic(self):
        subject = self.topic_subject_var.get().strip()
        topic_name = self.topic_name_var.get().strip()
        progress = safe_int(self.topic_progress_var.get(), 0)
        if not subject or not topic_name or progress < 0 or progress > 100:
            messagebox.showerror(
                "Invalid topic", "Enter subject, topic, and progress from 0 to 100."
            )
            return
        topic = {
            "id": self.store.next_id("topic"),
            "subject": subject,
            "topic": topic_name,
            "progress": progress,
            "notes": self.topic_notes_text.get("1.0", "end").strip(),
        }
        self.profile["topics"].append(topic)
        self.store.save()
        self.topic_subject_var.set("")
        self.topic_name_var.set("")
        self.topic_progress_var.set("0")
        self.topic_notes_text.delete("1.0", "end")
        self.refresh_everything()

    def delete_topic(self):
        topic_id = self.selected_tree_id(self.topic_tree)
        if topic_id is None:
            return
        self.profile["topics"] = [
            topic
            for topic in self.profile["topics"]
            if safe_int(topic["id"]) != topic_id
        ]
        self.store.save()
        self.refresh_everything()

    def shift_topic_progress(self, delta):
        topic_id = self.selected_tree_id(self.topic_tree)
        if topic_id is None:
            return
        for topic in self.profile["topics"]:
            if safe_int(topic["id"]) == topic_id:
                topic["progress"] = max(
                    0, min(100, safe_int(topic["progress"]) + delta)
                )
                break
        self.store.save()
        self.refresh_everything()

    def refresh_topics(self):
        for item in self.topic_tree.get_children():
            self.topic_tree.delete(item)
        for topic in sorted(
            self.profile["topics"], key=lambda topic: (topic["subject"], topic["topic"])
        ):
            self.topic_tree.insert(
                "",
                "end",
                values=(
                    topic["id"],
                    topic["subject"],
                    topic["topic"],
                    f"{topic['progress']}%",
                ),
            )

    def save_template(self):
        name = simpledialog.askstring(
            "Template name", "Save current session setup as:", parent=self.root
        )
        if not name:
            return
        template = {
            "id": self.store.next_id("template"),
            "name": name.strip(),
            "subject": self.subject_var.get().strip() or "General",
            "minutes": safe_int(self.minutes_var.get(), 25),
            "tags": self.parse_tags(self.tags_var.get()),
            "notes": self.session_note_text.get("1.0", "end").strip(),
            "preset": self.preset_var.get(),
        }
        self.profile["templates"].append(template)
        self.store.save()
        self.refresh_everything()

    def delete_template(self):
        template_id = self.selected_tree_id(self.template_tree)
        if template_id is None:
            return
        self.profile["templates"] = [
            template
            for template in self.profile["templates"]
            if safe_int(template["id"]) != template_id
        ]
        self.store.save()
        self.refresh_everything()

    def apply_template_choice(self):
        template_id = self.template_labels.get(self.template_var.get())
        if template_id is None:
            return
        for template in self.profile["templates"]:
            if safe_int(template["id"]) == template_id:
                self.apply_template(template)
                break

    def apply_template_from_tree(self):
        template_id = self.selected_tree_id(self.template_tree)
        if template_id is None:
            return
        for template in self.profile["templates"]:
            if safe_int(template["id"]) == template_id:
                self.apply_template(template)
                break

    def apply_template(self, template):
        self.subject_var.set(template["subject"])
        self.minutes_var.set(str(template["minutes"]))
        self.tags_var.set(", ".join(template["tags"]))
        self.preset_var.set(template.get("preset", "Custom"))
        self.session_note_text.delete("1.0", "end")
        self.session_note_text.insert("1.0", template.get("notes", ""))
        self.status_var.set(f"Template loaded: {template['name']}")

    def refresh_history(self):
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        sessions = list(reversed(self.profile["sessions"]))
        query = self.history_search_var.get().strip().lower()
        status_filter = self.history_status_var.get()
        for index, session in enumerate(sessions):
            if status_filter != "all" and session.get("status") != status_filter:
                continue
            haystack = " ".join(
                [
                    session.get("subject", ""),
                    session.get("task_title", ""),
                    session.get("note", ""),
                    session.get("reflection", ""),
                    " ".join(session.get("tags", [])),
                ]
            ).lower()
            if query and query not in haystack:
                continue
            ended = parse_iso(session.get("ended_at"))
            ended_label = ended.strftime("%Y-%m-%d %H:%M") if ended else ""
            self.history_tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    ended_label,
                    session.get("subject", ""),
                    session.get("task_title", ""),
                    session.get("studied_minutes", 0),
                    session.get("focus_score", "") or "-",
                    session.get("status", ""),
                    ", ".join(session.get("tags", [])),
                ),
            )

    def show_history_note(self):
        selected = self.history_tree.selection()
        if not selected:
            return
        index = int(selected[0])
        session = list(reversed(self.profile["sessions"]))[index]
        lines = [
            f"Note: {session.get('note', '') or 'No note'}",
            f"Reflection: {session.get('reflection', '') or 'No reflection'}",
            f"Next Step: {session.get('next_step', '') or 'No next step'}",
            f"Distractions: {', '.join(session.get('distractions', [])) or 'None logged'}",
            f"Template: {session.get('template_name', '') or 'None'}",
        ]
        self.history_note_text.configure(state="normal")
        self.history_note_text.delete("1.0", "end")
        self.history_note_text.insert("1.0", "\n".join(lines))
        self.history_note_text.configure(state="disabled")

    def save_settings(self):
        self.profile["goals"]["daily_minutes"] = safe_int(
            self.daily_goal_var.get(), 120
        )
        self.profile["goals"]["weekly_sessions"] = safe_int(
            self.weekly_goal_var.get(), 10
        )
        self.profile["settings"]["breaks_enabled"] = bool(self.breaks_var.get())
        self.profile["settings"]["notifications_enabled"] = bool(
            self.notifications_var.get()
        )
        self.profile["settings"]["sound_cues"] = bool(self.sound_var.get())
        self.store.save()
        self.refresh_everything()

    def add_subject_goal(self):
        subject = self.subject_goal_var.get().strip()
        minutes = safe_int(self.subject_goal_minutes_var.get(), 0)
        if not subject or minutes <= 0:
            messagebox.showerror(
                "Invalid goal", "Enter a subject and a positive minute target."
            )
            return
        self.profile["goals"]["subject_minutes"][subject] = minutes
        self.subject_goal_var.set("")
        self.subject_goal_minutes_var.set("")
        self.store.save()
        self.refresh_everything()

    def delete_subject_goal(self):
        selected = self.subject_goal_tree.selection()
        if not selected:
            return
        subject = self.subject_goal_tree.item(selected[0], "values")[0]
        self.profile["goals"]["subject_minutes"].pop(subject, None)
        self.store.save()
        self.refresh_everything()

    def refresh_subject_goals(self):
        for item in self.subject_goal_tree.get_children():
            self.subject_goal_tree.delete(item)
        progress = self.subject_goal_progress()
        for subject, minutes in sorted(
            self.profile["goals"]["subject_minutes"].items()
        ):
            self.subject_goal_tree.insert(
                "",
                "end",
                values=(
                    subject,
                    f"{minutes} min",
                    f"{int(progress.get(subject, 0))}/{minutes} min",
                ),
            )

    def subject_goal_progress(self):
        today = now_local().date()
        week_start = today - timedelta(days=today.weekday())
        totals = defaultdict(float)
        for session in self.profile["sessions"]:
            ended = parse_iso(session.get("ended_at"))
            if not ended:
                continue
            if (
                session.get("status") == "completed"
                and session.get("session_type") == "focus"
            ):
                if week_start <= ended.date() <= today:
                    totals[session["subject"]] += float(
                        session.get("studied_minutes", 0)
                    )
        return totals

    def restore_active_session(self):
        active = self.profile.get("active_session")
        if not active:
            self.update_timer_display()
            return
        self.subject_var.set(active.get("subject", ""))
        self.minutes_var.set(str(active.get("planned_minutes", 25)))
        self.tags_var.set(", ".join(active.get("tags", [])))
        self.preset_var.set(active.get("preset_name", "Custom"))
        self.session_note_text.delete("1.0", "end")
        self.session_note_text.insert("1.0", active.get("note", ""))
        if active.get("task_title"):
            self.task_var.set(f"{active['task_title']} [{active.get('subject', '')}]")
        self.status_var.set("Recovered your saved session.")
        self.update_timer_display()
        self.start_tick_loop()

    def start_session(self):
        if self.profile.get("active_session"):
            messagebox.showinfo(
                "Session already active",
                "Finish, cancel, or resume the current timer first.",
            )
            return
        minutes = safe_int(self.minutes_var.get(), 0)
        if minutes <= 0:
            messagebox.showerror(
                "Invalid session", "Minutes must be a positive number."
            )
            return
        preset = POMODORO_PRESETS.get(self.preset_var.get(), POMODORO_PRESETS["Custom"])
        task_id = self.task_labels.get(self.task_var.get())
        task_title = ""
        if task_id:
            for task in self.profile["tasks"]:
                if safe_int(task["id"]) == safe_int(task_id):
                    task_title = task["title"]
                    break
        timestamp = now_local().isoformat()
        active = {
            "subject": self.subject_var.get().strip() or "General",
            "planned_minutes": minutes,
            "total_seconds": minutes * 60,
            "remaining_seconds": minutes * 60,
            "state": "running",
            "started_at": timestamp,
            "updated_at": timestamp,
            "session_type": "focus",
            "preset_name": self.preset_var.get(),
            "task_id": task_id,
            "task_title": task_title,
            "tags": self.parse_tags(self.tags_var.get()),
            "note": self.session_note_text.get("1.0", "end").strip(),
            "template_name": (
                ""
                if self.template_var.get() == "No template"
                else self.template_var.get()
            ),
            "cycle_count": 0,
            "distractions": [],
            "break_plan": {
                "short_break": preset["short_break"],
                "long_break": preset["long_break"],
                "long_break_after": preset["long_after"],
                "enabled": bool(self.breaks_var.get()),
            },
        }
        self.profile["active_session"] = active
        self.store.save()
        self.status_var.set(
            f"Started {minutes}-minute focus session for {active['subject']}."
        )
        self.update_timer_display()
        self.start_tick_loop()

    def start_tick_loop(self):
        if self.tick_job is None:
            self.tick()

    def tick(self):
        self.tick_job = None
        active = self.profile.get("active_session")
        if not active:
            self.update_timer_display()
            return
        if active["state"] == "running":
            previous = parse_iso(active.get("updated_at")) or now_local()
            current = now_local()
            elapsed = int((current - previous).total_seconds())
            if elapsed > 0:
                active["remaining_seconds"] = max(
                    0, safe_int(active["remaining_seconds"]) - elapsed
                )
                active["updated_at"] = current.isoformat()
                self.store.save()
            if safe_int(active["remaining_seconds"]) <= 0:
                self.complete_timer()
                return
        self.update_timer_display()
        self.tick_job = self.root.after(1000, self.tick)

    def update_timer_display(self):
        active = self.profile.get("active_session")
        if not active:
            self.timer_var.set("00:00")
            self.timer_subtitle_var.set("No active timer")
            self.progress_var.set(0)
            self.summary_var.set(self.dashboard_summary())
            return
        remaining = safe_int(active["remaining_seconds"])
        total = safe_int(
            active.get("total_seconds", active.get("planned_minutes", 25) * 60)
        )
        mins, secs = divmod(remaining, 60)
        self.timer_var.set(f"{mins:02d}:{secs:02d}")
        kind = "Focus" if active.get("session_type") == "focus" else "Break"
        self.timer_subtitle_var.set(
            f"{kind} • {active['subject']} • {active['state'].title()}"
        )
        task_text = active.get("task_title") or "No linked task"
        tags = ", ".join(active.get("tags", [])) or "No tags"
        self.summary_var.set(f"Task: {task_text} | Tags: {tags}")
        # Update progress bar
        if total > 0:
            progress = ((total - remaining) / total) * 100
            self.progress_var.set(progress)
        else:
            self.progress_var.set(0)

    def toggle_pause(self):
        active = self.profile.get("active_session")
        if not active:
            self.status_var.set("No active session to pause or resume.")
            return
        active["state"] = "paused" if active["state"] == "running" else "running"
        active["updated_at"] = now_local().isoformat()
        self.store.save()
        self.status_var.set(f"Timer {active['state']}.")
        self.update_timer_display()

    def extend_session(self):
        active = self.profile.get("active_session")
        if not active:
            return
        active["remaining_seconds"] = safe_int(active["remaining_seconds"]) + 300
        active["total_seconds"] = safe_int(active["total_seconds"]) + 300
        active["planned_minutes"] = round(safe_int(active["total_seconds"]) / 60)
        active["updated_at"] = now_local().isoformat()
        self.store.save()
        self.update_timer_display()

    def finish_now(self):
        active = self.profile.get("active_session")
        if not active:
            return
        active["remaining_seconds"] = 0
        active["updated_at"] = now_local().isoformat()
        self.complete_timer()

    def skip_break(self):
        active = self.profile.get("active_session")
        if not active or active.get("session_type") != "break":
            self.status_var.set("No break to skip.")
            return
        self.profile["active_session"] = None
        self.store.save()
        self.status_var.set("Break skipped.")
        self.refresh_everything()

    def cancel_session(self):
        active = self.profile.get("active_session")
        if not active:
            return
        entry = self.build_session_entry(active, "cancelled")
        self.profile["sessions"].append(entry)
        self.profile["active_session"] = None
        self.store.save()
        self.status_var.set("Session cancelled and saved.")
        self.refresh_everything()

    def log_distraction(self):
        active = self.profile.get("active_session")
        if not active or active.get("session_type") != "focus":
            self.status_var.set("Log distractions during a focus session.")
            return
        choice = simpledialog.askstring(
            "Distraction",
            "Distraction type (Phone, Noise, Social Media, Tired, Multitasking, Other):",
            parent=self.root,
        )
        if not choice:
            return
        active.setdefault("distractions", []).append(choice.strip())
        self.store.save()
        self.status_var.set(f"Logged distraction: {choice.strip()}")

    def build_session_entry(self, active, status):
        ended = now_local().isoformat()
        total_seconds = safe_int(active.get("total_seconds"), 0)
        remaining = safe_int(active.get("remaining_seconds"), 0)
        studied_seconds = (
            total_seconds
            if status == "completed"
            else max(0, total_seconds - remaining)
        )
        return {
            "subject": active.get("subject", "General"),
            "planned_minutes": active.get("planned_minutes", 0),
            "studied_minutes": round(studied_seconds / 60, 1),
            "status": status,
            "started_at": active.get("started_at", ended),
            "ended_at": ended,
            "note": active.get("note", ""),
            "tags": active.get("tags", []),
            "task_id": active.get("task_id"),
            "task_title": active.get("task_title", ""),
            "session_type": active.get("session_type", "focus"),
            "template_name": active.get("template_name", ""),
            "focus_score": None,
            "reflection": "",
            "next_step": "",
            "distractions": active.get("distractions", []),
        }

    def complete_timer(self):
        active = self.profile.get("active_session")
        if not active:
            return
        if active.get("session_type") == "focus":
            entry = self.build_session_entry(active, "completed")
            self.collect_reflection(entry)
            self.profile["sessions"].append(entry)
            self.store.apply_session_to_task(self.profile, entry)
            self.profile["active_session"] = None
            self.start_break_if_needed(active)
            self.unlock_achievements()
            self.notify("Focus session complete", f"{entry['subject']} session saved.")
        else:
            self.profile["active_session"] = None
            self.notify(
                "Break complete", "Break finished. Time for the next study block."
            )
        self.store.save()
        self.refresh_everything()

    def collect_reflection(self, entry):
        focus_score = simpledialog.askinteger(
            "Focus score",
            "Rate focus from 1 to 10:",
            parent=self.root,
            minvalue=1,
            maxvalue=10,
        )
        reflection = simpledialog.askstring(
            "Reflection", "What went well in this session?", parent=self.root
        )
        next_step = simpledialog.askstring(
            "Next step", "What should you do next?", parent=self.root
        )
        entry["focus_score"] = focus_score
        entry["reflection"] = reflection or ""
        entry["next_step"] = next_step or ""

    def start_break_if_needed(self, focus_session):
        if not self.breaks_var.get():
            self.status_var.set("Session complete. Auto breaks are off.")
            return
        plan = focus_session.get("break_plan", {})
        cycle = safe_int(focus_session.get("cycle_count"), 0) + 1
        after = max(1, safe_int(plan.get("long_break_after"), 4))
        is_long = cycle % after == 0
        break_minutes = safe_int(
            plan.get("long_break" if is_long else "short_break"), 5
        )
        timestamp = now_local().isoformat()
        self.profile["active_session"] = {
            "subject": "Long Break" if is_long else "Short Break",
            "planned_minutes": break_minutes,
            "total_seconds": break_minutes * 60,
            "remaining_seconds": break_minutes * 60,
            "state": "running",
            "started_at": timestamp,
            "updated_at": timestamp,
            "session_type": "break",
            "preset_name": focus_session.get("preset_name", "Custom"),
            "task_id": focus_session.get("task_id"),
            "task_title": focus_session.get("task_title", ""),
            "tags": focus_session.get("tags", []),
            "note": "",
            "template_name": focus_session.get("template_name", ""),
            "cycle_count": cycle,
            "distractions": [],
            "break_plan": plan,
        }
        self.status_var.set(
            f"Started {'long' if is_long else 'short'} break for {break_minutes} minutes."
        )
        self.start_tick_loop()

    def unlock_achievements(self):
        completed = [
            session
            for session in self.profile["sessions"]
            if session.get("status") == "completed"
            and session.get("session_type") == "focus"
        ]
        achievements = []
        total_minutes = sum(
            float(session.get("studied_minutes", 0)) for session in completed
        )
        if len(completed) >= 1:
            achievements.append("First Focus Session")
        if len(completed) >= 10:
            achievements.append("Ten Session Builder")
        if total_minutes >= 600:
            achievements.append("Ten Hour Club")
        if self.calculate_streak() >= 7:
            achievements.append("Seven Day Streak")
        if achievements:
            self.status_var.set(f"Achievement unlocked: {achievements[-1]}")

    def calculate_streak(self):
        active_days = set()
        for session in self.profile["sessions"]:
            ended = parse_iso(session.get("ended_at"))
            if (
                ended
                and session.get("status") == "completed"
                and session.get("session_type") == "focus"
            ):
                active_days.add(ended.date())
        streak = 0
        day = now_local().date()
        while day in active_days:
            streak += 1
            day -= timedelta(days=1)
        return streak

    def refresh_dashboard(self):
        today = now_local().date()
        week_start = today - timedelta(days=today.weekday())
        focus_sessions = [
            session
            for session in self.profile["sessions"]
            if session.get("status") == "completed"
            and session.get("session_type") == "focus"
        ]
        minutes_today = sum(
            float(session["studied_minutes"])
            for session in focus_sessions
            if (ended := parse_iso(session.get("ended_at"))) and ended.date() == today
        )
        sessions_week = [
            session
            for session in focus_sessions
            if (ended := parse_iso(session.get("ended_at")))
            and week_start <= ended.date() <= today
        ]
        by_subject: defaultdict[str, float] = defaultdict(float)
        by_day: defaultdict[str, float] = defaultdict(float)
        focus_scores = []
        tag_counts = Counter()
        distraction_counts = Counter()
        for session in sessions_week:
            by_subject[session["subject"]] += float(session["studied_minutes"])
            if ended := parse_iso(session["ended_at"]):
                by_day[ended.strftime("%a")] += float(session["studied_minutes"])
            if session.get("focus_score"):
                focus_scores.append(session["focus_score"])
            tag_counts.update(session.get("tags", []))
            distraction_counts.update(session.get("distractions", []))

        top_subject = (
            max(by_subject.items(), key=lambda item: item[1])[0]
            if by_subject
            else "None yet"
        )
        avg_focus = (
            round(sum(focus_scores) / len(focus_scores), 1) if focus_scores else "-"
        )
        lines = [
            f"Today: {minutes_to_label(minutes_today)} / {minutes_to_label(self.profile['goals']['daily_minutes'])}",
            f"This week: {len(sessions_week)} sessions / {self.profile['goals']['weekly_sessions']}",
            f"Current streak: {self.calculate_streak()} day(s)",
            f"Top subject this week: {top_subject}",
            f"Average focus score: {avg_focus}",
            f"Most common tags: {', '.join(tag for tag, _ in tag_counts.most_common(4)) or 'None'}",
            f"Main distractions: {', '.join(tag for tag, _ in distraction_counts.most_common(3)) or 'None'}",
            f"Open tasks: {len([task for task in self.profile['tasks'] if task['status'] == 'open'])}",
        ]
        self.dashboard_text.configure(state="normal")
        self.dashboard_text.delete("1.0", "end")
        self.dashboard_text.insert("1.0", "\n".join(lines))
        self.dashboard_text.configure(state="disabled")
        self.draw_charts(by_subject, by_day)
        self.summary_var.set(self.dashboard_summary())

    def draw_charts(self, by_subject, by_day):
        self.chart_canvas.delete("all")
        width = max(self.chart_canvas.winfo_width(), 700)
        height = max(self.chart_canvas.winfo_height(), 240)
        self.chart_canvas.create_text(
            20,
            20,
            anchor="w",
            text="Study minutes by subject",
            fill=self.theme["text"],
            font=("Avenir Next", 12, "bold"),
        )
        self.chart_canvas.create_text(
            width // 2 + 20,
            20,
            anchor="w",
            text="Study minutes by weekday",
            fill=self.theme["text"],
            font=("Avenir Next", 12, "bold"),
        )

        subject_items = list(by_subject.items())[:5]
        max_subject = max([value for _name, value in subject_items] + [1])
        x = 20
        for name, value in subject_items:
            bar_height = 150 * (value / max_subject)
            self.chart_canvas.create_rectangle(
                x, 190 - bar_height, x + 70, 190, fill=self.theme["accent"], outline=""
            )
            self.chart_canvas.create_text(
                x + 35,
                205,
                text=name[:10],
                fill=self.theme["text"],
                font=("Avenir Next", 10),
            )
            self.chart_canvas.create_text(
                x + 35,
                190 - bar_height - 12,
                text=int(value),
                fill=self.theme["text"],
                font=("Avenir Next", 9),
            )
            x += 90

        weekday_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        max_day = max([by_day.get(day, 0) for day in weekday_order] + [1])
        x = width // 2 + 20
        for day in weekday_order:
            value = by_day.get(day, 0)
            bar_height = 150 * (value / max_day)
            self.chart_canvas.create_rectangle(
                x, 190 - bar_height, x + 40, 190, fill="#d98b5f", outline=""
            )
            self.chart_canvas.create_text(
                x + 20, 205, text=day, fill=self.theme["text"], font=("Avenir Next", 9)
            )
            if value:
                self.chart_canvas.create_text(
                    x + 20,
                    190 - bar_height - 12,
                    text=int(value),
                    fill=self.theme["text"],
                    font=("Avenir Next", 9),
                )
            x += 55

    def dashboard_summary(self):
        focus_sessions = [
            session
            for session in self.profile["sessions"]
            if session.get("status") == "completed"
            and session.get("session_type") == "focus"
        ]
        total_minutes = int(
            sum(float(session.get("studied_minutes", 0)) for session in focus_sessions)
        )
        return f"Total focused time: {minutes_to_label(total_minutes)} | Tasks: {len(self.profile['tasks'])} | Plans: {len(self.profile['plans'])}"

    def refresh_review(self):
        today = now_local().date()
        open_tasks = [task for task in self.sorted_tasks() if task["status"] == "open"]
        upcoming_exams = sorted(
            [exam for exam in self.profile["exams"] if exam.get("date")],
            key=lambda exam: exam["date"],
        )
        today_label = today.strftime("%A")
        todays_plans = [
            plan
            for plan in self.profile["plans"]
            if today_label[:3] in [day[:3] for day in plan["days"]]
        ]
        recommendation = self.recommend_next_session()
        lines = [
            f"Daily review for {today.isoformat()}",
            "",
            "Recommended next move:",
            recommendation,
            "",
            "Today's recurring plans:",
        ]
        if todays_plans:
            for plan in todays_plans:
                lines.append(
                    f"- {plan['subject']} for {plan['minutes']} min at {plan.get('time') or 'any time'}"
                )
        else:
            lines.append("- No recurring plans scheduled today")

        lines.append("")
        lines.append("Most urgent tasks:")
        if open_tasks:
            for task in open_tasks[:5]:
                lines.append(
                    f"- {task['title']} [{task['subject']}] due {task.get('due_date') or 'no date'}"
                )
        else:
            lines.append("- No open tasks")

        lines.append("")
        lines.append("Upcoming exams:")
        if upcoming_exams:
            for exam in upcoming_exams[:4]:
                lines.append(f"- {exam['name']} [{exam['subject']}] on {exam['date']}")
        else:
            lines.append("- No exams added yet")

        lines.append("")
        lines.append("Growth reminders:")
        lines.extend(
            [
                "- Use tags consistently so your analytics get smarter.",
                "- Add a quick reflection after each session for better long-term feedback.",
                "- Update syllabus progress weekly so recommendations stay relevant.",
            ]
        )
        self.review_text.configure(state="normal")
        self.review_text.delete("1.0", "end")
        self.review_text.insert("1.0", "\n".join(lines))
        self.review_text.configure(state="disabled")

    def recommend_next_session(self):
        open_tasks = [task for task in self.sorted_tasks() if task["status"] == "open"]
        if open_tasks:
            task = open_tasks[0]
            return f"Start a {max(25, 50 if self.priority_score(task) > 30 else 25)} minute session on {task['title']}."
        incomplete_topics = [
            topic
            for topic in self.profile["topics"]
            if safe_int(topic["progress"]) < 100
        ]
        if incomplete_topics:
            topic = sorted(
                incomplete_topics, key=lambda item: safe_int(item["progress"])
            )[0]
            return f"Review topic '{topic['topic']}' in {topic['subject']} and push it 10% further."
        exams = sorted(
            self.profile["exams"], key=lambda exam: exam.get("date") or "9999-12-31"
        )
        if exams:
            return f"Do an exam-prep block for {exams[0]['subject']} because {exams[0]['name']} is upcoming."
        return "Pick a subject you have ignored recently and start a 25 minute reset session."

    def export_csv(self):
        fields = [
            "subject",
            "task_title",
            "planned_minutes",
            "studied_minutes",
            "session_type",
            "status",
            "started_at",
            "ended_at",
            "focus_score",
            "tags",
            "note",
            "reflection",
            "next_step",
            "distractions",
        ]
        with CSV_EXPORT.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            for session in self.profile["sessions"]:
                row = dict(session)
                row["tags"] = ", ".join(session.get("tags", []))
                row["distractions"] = ", ".join(session.get("distractions", []))
                writer.writerow({field: row.get(field, "") for field in fields})
        self.status_var.set(f"CSV exported to {CSV_EXPORT.name}")
        self.notify("CSV export complete", f"Saved {CSV_EXPORT.name}.")

    def export_report(self):
        report = self.generate_report_html()
        REPORT_EXPORT.write_text(report, encoding="utf-8")
        self.status_var.set(f"Printable report exported to {REPORT_EXPORT.name}")
        self.notify("Report export complete", f"Saved {REPORT_EXPORT.name:}")

    def generate_report_html(self):
        focus_sessions = [
            session
            for session in self.profile["sessions"]
            if session.get("status") == "completed"
            and session.get("session_type") == "focus"
        ]
        total_minutes = int(
            sum(float(session.get("studied_minutes", 0)) for session in focus_sessions)
        )
        task_rows = "".join(
            f"<tr><td>{task['title']}</td><td>{task['subject']}</td><td>{task.get('due_date', '')}</td><td>{task['status']}</td></tr>"
            for task in self.profile["tasks"][:20]
        )
        session_rows = "".join(
            f"<tr><td>{session.get('ended_at', '')[:10]}</td><td>{session.get('subject', '')}</td><td>{session.get('studied_minutes', 0)}</td><td>{session.get('focus_score', '') or '-'}</td></tr>"
            for session in reversed(self.profile["sessions"][-20:])
        )
        return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Study Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #222; }}
    h1, h2 {{ color: #215145; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 24px; }}
    th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
    .meta {{ margin-bottom: 24px; }}
  </style>
</head>
<body>
  <h1>Study Report: {self.profile_var.get()}</h1>
  <div class="meta">
    <p>Total focused time: {minutes_to_label(total_minutes)}</p>
    <p>Current streak: {self.calculate_streak()} days</p>
    <p>Open tasks: {len([task for task in self.profile['tasks'] if task['status'] == 'open'])}</p>
  </div>
  <h2>Tasks</h2>
  <table><tr><th>Title</th><th>Subject</th><th>Due</th><th>Status</th></tr>{task_rows}</table>
  <h2>Recent Sessions</h2>
  <table><tr><th>Date</th><th>Subject</th><th>Minutes</th><th>Focus Score</th></tr>{session_rows}</table>
</body>
</html>"""

    def notify(self, title, message):
        if not self.notifications_var.get():
            return
        if self.sound_var.get():
            self.root.bell()
        if self.notification_open:
            return
        self.notification_open = True
        try:
            messagebox.showinfo(title, message)
        finally:
            self.notification_open = False

    def on_close(self):
        active = self.profile.get("active_session")
        if active:
            active["updated_at"] = now_local().isoformat()
        self.store.save()
        self.root.destroy()

    def show_preferences(self):
        # Simple preferences dialog
        pref_win = tk.Toplevel(self.root)
        pref_win.title("Preferences")
        pref_win.geometry("400x300")
        ttk.Label(pref_win, text="Preferences", font=("Avenir Next", 16, "bold")).pack(
            pady=10
        )
        ttk.Checkbutton(pref_win, text="Enable Breaks", variable=self.breaks_var).pack(
            pady=5
        )
        ttk.Checkbutton(
            pref_win, text="Enable Notifications", variable=self.notifications_var
        ).pack(pady=5)
        ttk.Checkbutton(pref_win, text="Sound Cues", variable=self.sound_var).pack(
            pady=5
        )
        ttk.Button(
            pref_win,
            text="Save",
            command=lambda: [self.save_settings(), pref_win.destroy()],
        ).pack(pady=10)

    def show_about(self):
        messagebox.showinfo(
            "About", "Study Helper v1.0\nA comprehensive study management app."
        )

    def run(self):
        self.root.mainloop()


def run_app():
    app = StudyApp()
    app.run()


if __name__ == "__main__":
    run_app()
