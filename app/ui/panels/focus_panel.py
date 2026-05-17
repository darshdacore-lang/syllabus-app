import sys
from pathlib import Path

import tkinter as tk
from tkinter import ttk, messagebox

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.utils.helpers import format_timer, join_tags, parse_tags, safe_int

PRESETS = {
    "Pomodoro 25/5": {
        "focus": 25,
        "short_break": 5,
        "long_break": 15,
        "long_break_after": 4,
    },
    "Deep Work 50/10": {
        "focus": 50,
        "short_break": 10,
        "long_break": 20,
        "long_break_after": 3,
    },
    "Quick Sprint 15/3": {
        "focus": 15,
        "short_break": 3,
        "long_break": 10,
        "long_break_after": 4,
    },
}


class FocusPanel:
    def __init__(
        self, parent, agent, session_engine, task_manager, on_status, on_data_changed
    ):
        self.agent = agent
        self.engine = session_engine
        self.task_manager = task_manager
        self.on_status = on_status
        self.on_data_changed = on_data_changed

        self.frame = ttk.Frame(parent, padding=18)

        defaults = self.engine.get_break_settings()

        # Vars
        self.timer_var = tk.StringVar(value="00:00")
        self.mode_var = tk.StringVar(value="Ready")
        self.subtitle_var = tk.StringVar(value="Pick a task or start focus")
        self.break_preview_var = tk.StringVar(value="")
        self.detail_var = tk.StringVar(value="")

        self.subject_var = tk.StringVar(value="General")
        self.task_var = tk.StringVar(value="")
        self.tags_var = tk.StringVar(value="")
        self.minutes_var = tk.StringVar(value="25")

        self.short_break_var = tk.StringVar(value=str(defaults["short_break"]))
        self.long_break_var = tk.StringVar(value=str(defaults["long_break"]))
        self.long_break_after_var = tk.StringVar(
            value=str(defaults["long_break_after"])
        )

        self.linked_task_var = tk.StringVar(value="Quick Session")
        self.task_lookup = {"Quick Session": None}

        self._build()

        self.refresh_task_choices()
        self.update_display(self.engine.get_active())

    # -------------------------
    # TASKS
    # -------------------------
    def refresh_task_choices(self):
        values = ["Quick Session"]
        self.task_lookup = {"Quick Session": None}

        for t in self.task_manager.task_choices():
            values.append(t["label"])
            self.task_lookup[t["label"]] = t["id"]

        self.linked_task_select["values"] = values

        if self.linked_task_var.get() not in self.task_lookup:
            self.linked_task_var.set("Quick Session")

    # -------------------------
    # BUILD UI
    # -------------------------
    def _build(self):
        self.frame.columnconfigure(1, weight=1)

        ttk.Label(self.frame, text="Focus Console", font=("Arial", 16, "bold")).grid(
            row=0, column=0, sticky="w"
        )

        ttk.Label(self.frame, textvariable=self.mode_var).grid(
            row=1, column=0, sticky="w"
        )
        ttk.Label(self.frame, textvariable=self.timer_var, font=("Arial", 28)).grid(
            row=2, column=0, sticky="w"
        )

        ttk.Label(self.frame, textvariable=self.subtitle_var).grid(
            row=3, column=0, sticky="w"
        )
        ttk.Label(self.frame, textvariable=self.break_preview_var).grid(
            row=4, column=0, sticky="w"
        )
        ttk.Label(self.frame, textvariable=self.detail_var).grid(
            row=5, column=0, sticky="w"
        )

        # Setup
        setup = ttk.LabelFrame(self.frame, text="Session Setup", padding=10)
        setup.grid(row=6, column=0, sticky="ew", pady=10)

        ttk.Label(setup, text="Minutes").grid(row=0, column=0)
        self.minutes_entry = ttk.Entry(setup, textvariable=self.minutes_var)
        self.minutes_entry.grid(row=0, column=1)

        ttk.Label(setup, text="Subject").grid(row=1, column=0)
        ttk.Entry(setup, textvariable=self.subject_var).grid(row=1, column=1)

        ttk.Label(setup, text="Task").grid(row=2, column=0)
        ttk.Entry(setup, textvariable=self.task_var).grid(row=2, column=1)

        ttk.Label(setup, text="Tags").grid(row=3, column=0)
        ttk.Entry(setup, textvariable=self.tags_var).grid(row=3, column=1)

        self.linked_task_select = ttk.Combobox(
            setup, textvariable=self.linked_task_var, state="readonly"
        )
        self.linked_task_select.grid(row=4, column=0, columnspan=2, sticky="ew")

        # Buttons
        btns = ttk.Frame(self.frame)
        btns.grid(row=7, column=0, sticky="ew")

        ttk.Button(btns, text="Start", command=self.start_focus).pack(side="left")
        ttk.Button(btns, text="Pause", command=self.toggle_pause).pack(side="left")
        ttk.Button(btns, text="Finish", command=self.finish_focus).pack(side="left")
        ttk.Button(btns, text="Skip", command=self.skip_break).pack(side="left")

    # -------------------------
    # DISPLAY
    # -------------------------
    def update_display(self, active):
        if not active:
            self.timer_var.set("00:00")
            self.mode_var.set("Ready")
            return

        remaining = safe_int(active.get("remaining_seconds"), 0)
        self.timer_var.set(format_timer(remaining))

        if active.get("session_type") == "focus":
            self.mode_var.set("Focus")
        else:
            self.mode_var.set("Break")

    # -------------------------
    # ACTIONS
    # -------------------------
    def start_focus(self):
        try:
            minutes = safe_int(self.minutes_var.get(), 25)
        except:
            minutes = 25

        subject = self.subject_var.get() or "General"
        task = self.task_var.get() or None
        tags = parse_tags(self.tags_var.get())

        active = self.agent.handle_command(
            "start_focus",
            subject=subject,
            minutes=minutes,
            task=task,
            task_id=self.task_lookup.get(self.linked_task_var.get()),
            tags=tags,
        )

        self.on_status("Focus started")
        self.on_data_changed()
        self.update_display(active)

    def toggle_pause(self):
        active = self.agent.handle_command("get_active")
        if not active:
            return

        if active.get("state") == "running":
            self.agent.handle_command("pause")
            self.on_status("Paused")
        else:
            self.agent.handle_command("resume")
            self.on_status("Resumed")

        self.update_display(self.agent.handle_command("get_active"))

    def finish_focus(self):
        active = self.engine.get_active()
        if not active:
            return

        self.engine.complete_focus(active)
        self.on_status("Finished focus")
        self.on_data_changed()

    def skip_break(self):
        active = self.engine.get_active()
        if not active:
            return

        self.engine.complete_break(active)
        self.on_status("Skipped break")
        self.on_data_changed()
