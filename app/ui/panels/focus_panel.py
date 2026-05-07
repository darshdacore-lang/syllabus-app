import tkinter as tk
from tkinter import messagebox, ttk

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
        self.frame = ttk.Frame(parent, style="App.TFrame", padding=18)

        defaults = self.engine.get_break_settings()
        self.task_lookup = {"Quick Session": None}

        self.timer_var = tk.StringVar(value="00:00")
        self.mode_var = tk.StringVar(value="Ready")
        self.subtitle_var = tk.StringVar(
            value="Pick a task or start a quick focus block."
        )
        self.break_preview_var = tk.StringVar(value="")
        self.detail_var = tk.StringVar(
            value="Link a task to roll minutes into your task list."
        )
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

        self._build()
        self.refresh_task_choices()
        self.update_display(self.engine.get_active())

    def _build(self):
        self.frame.columnconfigure(0, weight=3)
        self.frame.columnconfigure(1, weight=2)
        self.show_advanced = tk.BooleanVar(value=False)

        hero = ttk.Frame(self.frame, style="Card.TFrame", padding=28)
        hero.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 12))

        ttk.Label(hero, text="Focus Console", style="Title.TLabel").pack(anchor="w")
        ttk.Label(hero, textvariable=self.mode_var, style="Muted.TLabel").pack(
            anchor="w", pady=(8, 0)
        )

        timer_frame = ttk.Frame(hero, style="Card.TFrame")
        timer_frame.pack(anchor="w", pady=(12, 0))
        ttk.Label(timer_frame, textvariable=self.timer_var, style="Hero.TLabel").pack(
            anchor="w"
        )

        ttk.Label(
            hero, textvariable=self.subtitle_var, style="Body.TLabel", wraplength=420
        ).pack(anchor="w", pady=(6, 0))
        ttk.Label(
            hero,
            textvariable=self.break_preview_var,
            style="Muted.TLabel",
            wraplength=420,
        ).pack(anchor="w", pady=(8, 0))
        ttk.Label(
            hero, textvariable=self.detail_var, style="Muted.TLabel", wraplength=420
        ).pack(anchor="w", pady=(4, 0))

        progress_card = ttk.LabelFrame(
            self.frame,
            text="Session Progress",
            style="Section.TLabelframe",
            padding=16,
        )
        progress_card.grid(row=0, column=1, sticky="nsew", pady=(0, 12))
        self.progress = ttk.Progressbar(progress_card, maximum=100, value=0, length=200)
        self.progress.pack(fill="x", pady=(0, 8))
        self.progress_label = ttk.Label(
            progress_card, text="0% complete", style="Body.TLabel"
        )
        self.progress_label.pack(anchor="w")

        quick_actions = ttk.Frame(self.frame, style="Card.TFrame", padding=(0, 0, 0, 0))
        quick_actions.grid(row=1, column=1, sticky="nsew", pady=(0, 0))
        ttk.Button(
            quick_actions,
            text="Start Focus",
            style="Accent.TButton",
            command=self.start_focus,
        ).pack(fill="x", pady=(4, 4))
        self.pause_button = ttk.Button(
            quick_actions,
            text="Pause",
            style="Subtle.TButton",
            command=self.toggle_pause,
        )
        self.pause_button.pack(fill="x", pady=(4, 4))
        self.finish_button = ttk.Button(
            quick_actions,
            text="Finish Focus",
            style="Subtle.TButton",
            command=self.finish_focus,
        )
        self.finish_button.pack(fill="x", pady=(4, 4))
        self.skip_button = ttk.Button(
            quick_actions,
            text="Skip Break",
            style="Subtle.TButton",
            command=self.skip_break,
        )
        self.skip_button.pack(fill="x", pady=(4, 4))

        setup = ttk.LabelFrame(
            self.frame,
            text="Session Setup",
            style="Section.TLabelframe",
            padding=16,
        )
        setup.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(12, 0))
        setup.columnconfigure(1, weight=1)
        setup.columnconfigure(3, weight=1)

        ttk.Label(setup, text="Linked Task", style="Body.TLabel").grid(
            row=0, column=0, sticky="w", pady=4
        )
        self.linked_task_select = ttk.Combobox(
            setup, textvariable=self.linked_task_var, state="readonly", width=40
        )
        self.linked_task_select.grid(row=0, column=1, columnspan=3, sticky="ew", pady=4)
        self.linked_task_select.bind(
            "<<ComboboxSelected>>", self._apply_selected_task_defaults
        )

        ttk.Label(setup, text="Subject", style="Body.TLabel").grid(
            row=1, column=0, sticky="w", pady=4
        )
        ttk.Entry(setup, textvariable=self.subject_var, width=20).grid(
            row=1, column=1, sticky="ew", pady=4
        )
        ttk.Label(setup, text="Task Title", style="Body.TLabel").grid(
            row=1, column=2, sticky="w", pady=4, padx=(12, 0)
        )
        ttk.Entry(setup, textvariable=self.task_var, width=20).grid(
            row=1, column=3, sticky="ew", pady=4
        )

        ttk.Label(setup, text="Focus Duration", style="Body.TLabel").grid(
            row=2, column=0, sticky="w", pady=4
        )
        ttk.Entry(setup, textvariable=self.minutes_var, width=20).grid(
            row=2, column=1, sticky="ew", pady=4
        )
        ttk.Label(setup, text=" minutes", style="Muted.TLabel").grid(
            row=2, column=2, sticky="w", pady=4, padx=(12, 0)
        )

        ttk.Label(setup, text="Tags", style="Body.TLabel").grid(
            row=3, column=0, sticky="w", pady=4
        )
        ttk.Entry(setup, textvariable=self.tags_var, width=20).grid(
            row=3, column=1, columnspan=3, sticky="ew", pady=4
        )

        presets = ttk.Frame(setup, style="Card.TFrame")
        presets.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(14, 6))
        ttk.Label(presets, text="Quick Presets", style="Body.TLabel").pack(anchor="w")
        buttons = ttk.Frame(presets, style="Card.TFrame")
        buttons.pack(anchor="w", pady=(8, 0), fill="x")
        for index, name in enumerate(PRESETS):
            style = "Accent.TButton" if index == 0 else "Subtle.TButton"
            ttk.Button(
                buttons,
                text=name,
                style=style,
                command=lambda preset=name: self._select_preset(preset),
            ).pack(side="left", padx=(0, 8))

        ttk.Button(
            setup,
            text="Show Advanced Settings",
            style="Subtle.TButton",
            command=self._toggle_advanced,
        ).grid(row=5, column=0, columnspan=4, sticky="ew", pady=(8, 0))

        self.advanced_frame = ttk.LabelFrame(
            setup,
            text="Break Schedule",
            style="Section.TLabelframe",
            padding=12,
        )
        self.advanced_frame.grid(
            row=6, column=0, columnspan=4, sticky="ew", pady=(8, 0)
        )
        self.advanced_frame.columnconfigure(1, weight=1)
        self.advanced_frame.columnconfigure(3, weight=1)

        ttk.Label(self.advanced_frame, text="Short Break", style="Body.TLabel").grid(
            row=0, column=0, sticky="w", pady=4
        )
        ttk.Entry(
            self.advanced_frame, textvariable=self.short_break_var, width=15
        ).grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Label(self.advanced_frame, text=" min", style="Muted.TLabel").grid(
            row=0, column=2, sticky="w", pady=4, padx=(4, 0)
        )

        ttk.Label(self.advanced_frame, text="Long Break", style="Body.TLabel").grid(
            row=0, column=3, sticky="w", pady=4, padx=(12, 0)
        )
        ttk.Entry(self.advanced_frame, textvariable=self.long_break_var, width=15).grid(
            row=0, column=4, sticky="ew", pady=4
        )
        ttk.Label(self.advanced_frame, text=" min", style="Muted.TLabel").grid(
            row=0, column=5, sticky="w", pady=4, padx=(4, 0)
        )

        ttk.Label(
            self.advanced_frame, text="Long Break Every", style="Body.TLabel"
        ).grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(
            self.advanced_frame, textvariable=self.long_break_after_var, width=15
        ).grid(row=1, column=1, sticky="ew", pady=4)
        ttk.Label(self.advanced_frame, text=" cycles", style="Muted.TLabel").grid(
            row=1, column=2, sticky="w", pady=4, padx=(4, 0)
        )

        preference_row = ttk.Frame(self.advanced_frame, style="Card.TFrame")
        preference_row.grid(row=2, column=0, columnspan=6, sticky="ew", pady=(12, 0))
        ttk.Button(
            preference_row,
            text="Save Defaults",
            style="Accent.TButton",
            command=self.save_break_defaults,
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            preference_row,
            text="Load Defaults",
            style="Subtle.TButton",
            command=self.load_break_defaults,
        ).pack(side="left")

        self._hide_advanced()

    def _toggle_advanced(self):
        if self.show_advanced.get():
            self._hide_advanced()
        else:
            self._show_advanced()

    def _show_advanced(self):
        self.show_advanced.set(True)
        self.advanced_frame.grid()

    def _hide_advanced(self):
        self.show_advanced.set(False)
        self.advanced_frame.grid_remove()

    def _select_preset(self, preset_name):
        preset = PRESETS[preset_name]
        self.minutes_var.set(str(preset["focus"]))
        self.short_break_var.set(str(preset["short_break"]))
        self.long_break_var.set(str(preset["long_break"]))
        self.long_break_after_var.set(str(preset["long_break_after"]))
        self.on_status(f"Preset selected: {preset_name}")
        self.update_display(self.engine.get_active())

    def _apply_selected_task_defaults(self, _event=None):
        task_id = self.task_lookup.get(self.linked_task_var.get())
        if not task_id:
            self.on_status(
                "Quick session selected. You can type any subject or task title."
            )
            return

        defaults = self.task_manager.get_focus_defaults(task_id)
        self.subject_var.set(defaults["subject"])
        self.task_var.set(defaults["task_title"])
        self.tags_var.set(join_tags(defaults["tags"]))
        self.on_status("Task details pulled into the focus setup.")

    def _parse_positive(self, value, label):
        parsed = safe_int(value, 0)
        if parsed <= 0:
            raise ValueError(f"{label} must be a positive whole number.")
        return parsed

    def _build_break_plan_override(self):
        return {
            "short_break": self._parse_positive(
                self.short_break_var.get(), "Short break"
            ),
            "long_break": self._parse_positive(self.long_break_var.get(), "Long break"),
            "long_break_after": self._parse_positive(
                self.long_break_after_var.get(),
                "Long break cadence",
            ),
        }

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

    def load_break_defaults(self):
        defaults = self.engine.get_break_settings()
        self.short_break_var.set(str(defaults["short_break"]))
        self.long_break_var.set(str(defaults["long_break"]))
        self.long_break_after_var.set(str(defaults["long_break_after"]))
        self.on_status("Loaded saved break defaults into the editor.")
        self.update_display(self.engine.get_active())

    def save_break_defaults(self):
        try:
            break_plan = self._build_break_plan_override()
            settings = self.engine.save_break_settings(
                break_plan["short_break"],
                break_plan["long_break"],
                break_plan["long_break_after"],
            )
        except ValueError as exc:
            messagebox.showerror("Invalid break settings", str(exc))
            return

        self.short_break_var.set(str(settings["short_break"]))
        self.long_break_var.set(str(settings["long_break"]))
        self.long_break_after_var.set(str(settings["long_break_after"]))
        self.on_status("Saved break defaults for future sessions.")
        self.update_display(self.engine.get_active())

    def start_focus(self):
        try:
            minutes = self._parse_positive(self.minutes_var.get(), "Focus minutes")
            break_plan = self._build_break_plan_override()
        except ValueError as exc:
            messagebox.showerror("Invalid session setup", str(exc))
            return

        subject = self.subject_var.get().strip() or "General"
        task_title = self.task_var.get().strip() or None
        task_id = self.task_lookup.get(self.linked_task_var.get())
        tags = parse_tags(self.tags_var.get())

        try:
            active = self.agent.handle_command(
                "start_focus",
                subject=subject,
                minutes=minutes,
                task=task_title,
                task_id=task_id,
                tags=tags,
                break_plan=break_plan,
            )
        except (RuntimeError, ValueError) as exc:
            messagebox.showinfo("Unable to start session", str(exc))
            self.on_status(str(exc))
            self.update_display(self.agent.handle_command("get_active"))
            return

        self.on_status(f"Custom focus started for {subject} ({minutes} min).")
        self.on_data_changed()
        self.update_display(active)

    def toggle_pause(self):
        active = self.agent.handle_command("get_active")
        if not active:
            return

        if active.get("state") == "running":
            self.agent.handle_command("pause")
            self.on_status("Session paused.")
        else:
            self.agent.handle_command("resume")
            self.on_status("Session resumed.")

        self.on_data_changed()
        self.update_display(self.agent.handle_command("get_active"))

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
        current_plan = None
        try:
            current_plan = self._build_break_plan_override()
        except ValueError:
            current_plan = None

        preview = self.agent.handle_command("next_break_preview")
        self.break_preview_var.set(preview["label"])

        if not active:
            self.mode_var.set("Ready for your next block")
            self.timer_var.set("00:00")
            self.subtitle_var.set(
                "Set any custom focus or break lengths you want, then start."
            )
            if current_plan:
                self.detail_var.set(
                    "Custom break flow: "
                    f"{current_plan['short_break']}m short, "
                    f"{current_plan['long_break']}m long, "
                    f"every {current_plan['long_break_after']} cycles."
                )
            else:
                self.detail_var.set(
                    "Linked task minutes will roll into task progress automatically."
                )
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
            task_title = (
                active.get("task_title") or active.get("task") or "Untitled task"
            )
            self.subtitle_var.set(f"{active.get('subject', 'General')} - {task_title}")
            tags = join_tags(active.get("tags", [])) or "No tags"
            self.detail_var.set(f"Tags: {tags}")
            self.finish_button.configure(state="normal")
            self.skip_button.configure(state="disabled")
        else:
            cycle = safe_int(active.get("cycle_count"), 0)
            self.mode_var.set(f"Break after cycle {cycle}")
            self.subtitle_var.set(active.get("subject") or "Break time")
            self.detail_var.set(
                "Stretch, reset, and come back ready for the next block."
            )
            self.finish_button.configure(state="disabled")
            self.skip_button.configure(state="normal")

        pause_text = "Pause" if active.get("state") == "running" else "Resume"
        self.pause_button.configure(state="normal", text=pause_text)
