import tkinter as tk
from tkinter import messagebox, ttk

from app.utils.helpers import format_timer, join_tags, parse_tags, safe_int


PRESETS = {
    "Pomodoro 25/5": {"focus": 25, "short_break": 5, "long_break": 15, "long_break_after": 4},
    "Deep Work 50/10": {"focus": 50, "short_break": 10, "long_break": 20, "long_break_after": 3},
    "Quick Sprint 15/3": {"focus": 15, "short_break": 3, "long_break": 10, "long_break_after": 4},
}


class FocusPanel:
    def __init__(self, parent, session_engine, task_manager, on_status, on_data_changed):
        self.engine = session_engine
        self.task_manager = task_manager
        self.on_status = on_status
        self.on_data_changed = on_data_changed
        self.frame = ttk.Frame(parent, style="App.TFrame", padding=18)

        self.break_plan_override = None
        self.task_lookup = {"Quick Session": None}

        self.timer_var = tk.StringVar(value="00:00")
        self.mode_var = tk.StringVar(value="Ready")
        self.subtitle_var = tk.StringVar(value="Pick a task or start a quick focus block.")
        self.break_preview_var = tk.StringVar(value="")
        self.detail_var = tk.StringVar(value="Link a task to roll minutes into your task list.")
        self.subject_var = tk.StringVar(value="General")
        self.task_var = tk.StringVar(value="")
        self.tags_var = tk.StringVar(value="")
        self.minutes_var = tk.StringVar(value="25")
        self.linked_task_var = tk.StringVar(value="Quick Session")

        self._build()
        self.refresh_task_choices()
        self.update_display(self.engine.get_active())

    def _build(self):
        self.frame.columnconfigure(0, weight=3)
        self.frame.columnconfigure(1, weight=2)

        hero = ttk.Frame(self.frame, style="Card.TFrame", padding=22)
        hero.grid(row=0, column=0, sticky="nsew", padx=(0, 12), pady=(0, 12))
        ttk.Label(hero, text="Focus Console", style="Title.TLabel").pack(anchor="w")
        ttk.Label(hero, textvariable=self.mode_var, style="Muted.TLabel").pack(anchor="w", pady=(6, 0))
        ttk.Label(hero, textvariable=self.timer_var, style="Hero.TLabel").pack(anchor="w", pady=(6, 0))
        ttk.Label(hero, textvariable=self.subtitle_var, style="Body.TLabel", wraplength=420).pack(
            anchor="w", pady=(4, 0)
        )
        ttk.Label(hero, textvariable=self.break_preview_var, style="Muted.TLabel", wraplength=420).pack(
            anchor="w", pady=(10, 0)
        )
        ttk.Label(hero, textvariable=self.detail_var, style="Muted.TLabel", wraplength=420).pack(
            anchor="w", pady=(6, 0)
        )

        progress_card = ttk.LabelFrame(
            self.frame,
            text="Session Rhythm",
            style="Section.TLabelframe",
            padding=16,
        )
        progress_card.grid(row=0, column=1, sticky="nsew", pady=(0, 12))
        self.progress = ttk.Progressbar(progress_card, maximum=100, value=0)
        self.progress.pack(fill="x")
        self.progress_label = ttk.Label(progress_card, text="0% complete", style="Body.TLabel")
        self.progress_label.pack(anchor="w", pady=(8, 0))
        ttk.Label(
            progress_card,
            text="Use presets for quick starts, or link an existing task for better study tracking.",
            style="Muted.TLabel",
            wraplength=260,
        ).pack(anchor="w", pady=(12, 0))

        setup = ttk.LabelFrame(
            self.frame,
            text="Session Setup",
            style="Section.TLabelframe",
            padding=16,
        )
        setup.grid(row=1, column=0, columnspan=2, sticky="nsew")
        setup.columnconfigure(1, weight=1)

        ttk.Label(setup, text="Linked Task", style="Body.TLabel").grid(row=0, column=0, sticky="w", pady=4)
        self.linked_task_select = ttk.Combobox(
            setup,
            textvariable=self.linked_task_var,
            state="readonly",
        )
        self.linked_task_select.grid(row=0, column=1, sticky="ew", pady=4)
        self.linked_task_select.bind("<<ComboboxSelected>>", self._apply_selected_task_defaults)

        ttk.Label(setup, text="Subject", style="Body.TLabel").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(setup, textvariable=self.subject_var).grid(row=1, column=1, sticky="ew", pady=4)

        ttk.Label(setup, text="Task Title", style="Body.TLabel").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(setup, textvariable=self.task_var).grid(row=2, column=1, sticky="ew", pady=4)

        ttk.Label(setup, text="Tags", style="Body.TLabel").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Entry(setup, textvariable=self.tags_var).grid(row=3, column=1, sticky="ew", pady=4)

        ttk.Label(setup, text="Minutes", style="Body.TLabel").grid(row=4, column=0, sticky="w", pady=4)
        ttk.Entry(setup, textvariable=self.minutes_var).grid(row=4, column=1, sticky="w", pady=4)

        presets = ttk.Frame(setup, style="Card.TFrame")
        presets.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(14, 6))
        ttk.Label(presets, text="Quick Presets", style="Body.TLabel").pack(anchor="w")
        buttons = ttk.Frame(presets, style="Card.TFrame")
        buttons.pack(anchor="w", pady=(8, 0))
        for index, (name, plan) in enumerate(PRESETS.items()):
            style = "Accent.TButton" if index == 0 else "Subtle.TButton"
            ttk.Button(
                buttons,
                text=name,
                style=style,
                command=lambda preset=name: self._select_preset(preset),
            ).pack(side="left", padx=(0, 8))

        actions = ttk.Frame(self.frame, style="App.TFrame", padding=(0, 16, 0, 0))
        actions.grid(row=2, column=0, columnspan=2, sticky="ew")
        ttk.Button(actions, text="Start Focus", style="Accent.TButton", command=self.start_focus).pack(
            side="left", padx=(0, 8)
        )
        self.pause_button = ttk.Button(actions, text="Pause", style="Subtle.TButton", command=self.toggle_pause)
        self.pause_button.pack(side="left", padx=(0, 8))
        self.finish_button = ttk.Button(
            actions,
            text="Finish Focus",
            style="Subtle.TButton",
            command=self.finish_focus,
        )
        self.finish_button.pack(side="left", padx=(0, 8))
        self.skip_button = ttk.Button(actions, text="Skip Break", style="Subtle.TButton", command=self.skip_break)
        self.skip_button.pack(side="left")

    def _select_preset(self, preset_name):
        preset = PRESETS[preset_name]
        self.break_plan_override = {
            "short_break": preset["short_break"],
            "long_break": preset["long_break"],
            "long_break_after": preset["long_break_after"],
        }
        self.minutes_var.set(str(preset["focus"]))
        self.on_status(f"Preset selected: {preset_name}")
        self.update_display(self.engine.get_active())

    def _apply_selected_task_defaults(self, _event=None):
        task_id = self.task_lookup.get(self.linked_task_var.get())
        if not task_id:
            self.on_status("Quick session selected. You can type any subject or task title.")
            return

        defaults = self.task_manager.get_focus_defaults(task_id)
        self.subject_var.set(defaults["subject"])
        self.task_var.set(defaults["task_title"])
        self.tags_var.set(join_tags(defaults["tags"]))
        self.on_status("Task details pulled into the focus setup.")

    def _parse_minutes(self):
        minutes = safe_int(self.minutes_var.get(), 0)
        return minutes if minutes > 0 else None

    def refresh_task_choices(self):
        values = ["Quick Session"]
        self.task_lookup = {"Quick Session": None}
        for choice in self.task_manager.task_choices():
            values.append(choice["label"])
            self.task_lookup[choice["label"]] = choice["id"]

        current = self.linked_task_var.get()
        self.linked_task_select["values"] = values
        if current not in self.task_lookup:
            self.linked_task_var.set("Quick Session")

    def start_focus(self):
        minutes = self._parse_minutes()
        if minutes is None:
            messagebox.showerror("Invalid minutes", "Minutes must be a positive whole number.")
            return

        subject = self.subject_var.get().strip() or "General"
        task_title = self.task_var.get().strip() or None
        task_id = self.task_lookup.get(self.linked_task_var.get())
        tags = parse_tags(self.tags_var.get())

        try:
            active = self.engine.start_focus(
                subject,
                minutes,
                task=task_title,
                task_id=task_id,
                tags=tags,
                break_plan=self.break_plan_override,
            )
        except (RuntimeError, ValueError) as exc:
            messagebox.showinfo("Unable to start session", str(exc))
            self.on_status(str(exc))
            self.update_display(self.engine.get_active())
            return

        self.on_status(f"Focus started for {subject} ({minutes} min).")
        self.on_data_changed()
        self.update_display(active)

    def toggle_pause(self):
        active = self.engine.get_active()
        if not active:
            return

        if active.get("state") == "running":
            self.engine.pause()
            self.on_status("Session paused.")
        else:
            self.engine.resume()
            self.on_status("Session resumed.")

        self.on_data_changed()
        self.update_display(self.engine.get_active())

    def finish_focus(self):
        active = self.engine.get_active()
        if not active or active.get("session_type") != "focus":
            return

        next_session = self.engine.complete_focus(active)
        if next_session:
            self.on_status("Focus completed. Break started automatically.")
        else:
            self.on_status("Focus completed.")

        self.on_data_changed()
        self.update_display(self.engine.get_active())

    def skip_break(self):
        active = self.engine.get_active()
        if not active or active.get("session_type") != "break":
            return

        self.engine.complete_break(active)
        self.on_status("Break skipped. You can start the next focus block.")
        self.on_data_changed()
        self.update_display(self.engine.get_active())

    def update_display(self, active):
        preview = self.engine.next_break_preview(active)
        self.break_preview_var.set(preview["label"])

        if not active:
            self.mode_var.set("Ready for your next block")
            self.timer_var.set("00:00")
            self.subtitle_var.set("Pick a task, choose a preset, and start.")
            self.detail_var.set("Linked task minutes will roll into task progress automatically.")
            self.progress["value"] = 0
            self.progress_label.configure(text="0% complete")
            self.pause_button.configure(state="disabled", text="Pause")
            self.finish_button.configure(state="disabled")
            self.skip_button.configure(state="disabled")
            return

        remaining = max(0, safe_int(active.get("remaining_seconds"), 0))
        total = max(1, safe_int(active.get("total_seconds"), 1))
        progress = max(0, min(100, int(100 * (1 - remaining / total))))
        self.timer_var.set(format_timer(remaining))
        self.progress["value"] = progress
        self.progress_label.configure(text=f"{progress}% complete")

        if active.get("session_type") == "focus":
            cycle = safe_int(active.get("cycle_count"), 0) + 1
            self.mode_var.set(f"Focus cycle {cycle}")
            task_title = active.get("task_title") or active.get("task") or "Untitled task"
            self.subtitle_var.set(f"{active.get('subject', 'General')} - {task_title}")
            tags = join_tags(active.get("tags", [])) or "No tags"
            self.detail_var.set(f"Tags: {tags}")
            self.finish_button.configure(state="normal")
            self.skip_button.configure(state="disabled")
        else:
            cycle = safe_int(active.get("cycle_count"), 0)
            self.mode_var.set(f"Break after cycle {cycle}")
            self.subtitle_var.set(active.get("subject") or "Break time")
            self.detail_var.set("Stretch, reset, and come back ready for the next block.")
            self.finish_button.configure(state="disabled")
            self.skip_button.configure(state="normal")

        pause_text = "Pause" if active.get("state") == "running" else "Resume"
        self.pause_button.configure(state="normal", text=pause_text)

