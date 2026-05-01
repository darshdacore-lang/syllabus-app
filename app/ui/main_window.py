from tkinter import Tk, Label, Button, StringVar, Frame, Entry, messagebox
from tkinter.ttk import Progressbar
from app.core.session_engine import SessionEngine


DEFAULT_MINUTES = 25
WINDOW_SIZE = "460x420"


class MainWindow:
    def __init__(self, session_engine: SessionEngine):
        self.engine = session_engine

        self.root = Tk()
        self.root.title("Pomodoro Syllabus")
        self.root.geometry(WINDOW_SIZE)
        self.root.resizable(False, False)

        # ── UI STATE ─────────────────────────
        self.timer_var = StringVar(value="00:00")
        self.mode_var = StringVar(value="IDLE")
        self.status_var = StringVar(value="Ready")
        self.subtitle_var = StringVar(value="No active timer")
        self.subject_var = StringVar(value="General")
        self.task_var = StringVar(value="")
        self.tags_var = StringVar(value="")
        self.minutes_var = StringVar(value=str(DEFAULT_MINUTES))
        self.progress_var = StringVar(value="0%")

        # ── HEADER ────────────────────────────
        Label(self.root, text="Pomodoro Timer", font=("Arial", 18, "bold")).pack(
            pady=(12, 4)
        )
        Label(self.root, textvariable=self.mode_var, font=("Arial", 14)).pack(
            pady=(0, 2)
        )
        Label(self.root, textvariable=self.timer_var, font=("Arial", 40)).pack(
            pady=(0, 4)
        )
        Label(self.root, textvariable=self.subtitle_var, font=("Arial", 10)).pack(
            pady=(0, 4)
        )
        Label(self.root, textvariable=self.status_var, font=("Arial", 10)).pack(
            pady=(0, 12)
        )

        # ── INPUT FORM ───────────────────────
        form_frame = Frame(self.root)
        form_frame.pack(padx=12, pady=0, fill="x")

        Label(form_frame, text="Subject:", anchor="w", width=10).grid(
            row=0, column=0, sticky="w"
        )
        Entry(form_frame, textvariable=self.subject_var, width=30).grid(
            row=0, column=1, pady=2, sticky="w"
        )

        Label(form_frame, text="Task:", anchor="w", width=10).grid(
            row=1, column=0, sticky="w"
        )
        Entry(form_frame, textvariable=self.task_var, width=30).grid(
            row=1, column=1, pady=2, sticky="w"
        )

        Label(form_frame, text="Tags:", anchor="w", width=10).grid(
            row=2, column=0, sticky="w"
        )
        Entry(form_frame, textvariable=self.tags_var, width=30).grid(
            row=2, column=1, pady=2, sticky="w"
        )

        Label(form_frame, text="Minutes:", anchor="w", width=10).grid(
            row=3, column=0, sticky="w"
        )
        Entry(form_frame, textvariable=self.minutes_var, width=10).grid(
            row=3, column=1, pady=2, sticky="w"
        )

        # ── PROGRESS BAR ─────────────────────
        progress_frame = Frame(self.root)
        progress_frame.pack(padx=12, pady=(12, 8), fill="x")
        self.progress_bar = Progressbar(
            progress_frame, maximum=100, value=0, length=420
        )
        self.progress_bar.pack(fill="x")
        Label(progress_frame, textvariable=self.progress_var, anchor="e").pack(
            pady=(4, 0), anchor="e"
        )

        # ── BUTTONS ──────────────────────────
        controls = Frame(self.root)
        controls.pack(pady=8)

        Button(controls, text="Start Focus", command=self.start_focus, width=12).pack(
            side="left", padx=4
        )
        Button(controls, text="Pause/Resume", command=self.toggle_pause, width=12).pack(
            side="left", padx=4
        )
        Button(controls, text="Finish Focus", command=self.finish_focus, width=12).pack(
            side="left", padx=4
        )
        Button(controls, text="Skip Break", command=self.skip_break, width=12).pack(
            side="left", padx=4
        )

        self.tick_loop()

    def _set_idle_display(self):
        self.mode_var.set("IDLE")
        self.timer_var.set("00:00")
        self.subtitle_var.set("No active timer")
        self.progress_bar["value"] = 0
        self.progress_var.set("0%")

    def _parse_minutes(self):
        try:
            minutes = int(self.minutes_var.get())
        except ValueError:
            return None
        return minutes if minutes > 0 else None

    def _display_cycle(self, active):
        cycle = max(1, int(active.get("cycle_count", 0)))
        if active.get("session_type") == "focus":
            return cycle + (0 if active.get("remaining_seconds", 0) <= 0 else 1)
        return cycle

    # ─────────────────────────────────────
    # ACTIONS
    # ─────────────────────────────────────
    def start_focus(self):
        minutes = self._parse_minutes()
        if minutes is None:
            self.status_var.set("Minutes must be a positive whole number.")
            messagebox.showerror("Invalid session", "Minutes must be a positive number.")
            return

        subject = self.subject_var.get().strip() or "General"
        task = self.task_var.get().strip() or None
        tags = [tag.strip() for tag in self.tags_var.get().split(",") if tag.strip()]

        try:
            active = self.engine.start_focus(subject, minutes, task=task, tags=tags)
        except (RuntimeError, ValueError) as exc:
            self.status_var.set(str(exc))
            messagebox.showinfo("Unable to start session", str(exc))
            self.update_display(self.engine.get_active())
            return

        self.status_var.set(f"Focus started: {subject} • {minutes} min")
        self.update_display(active)

    def toggle_pause(self):
        active = self.engine.get_active()
        if not active:
            return

        if active.get("state") == "running":
            self.engine.pause()
            self.status_var.set("Paused ⏸")
        else:
            self.engine.resume()
            self.status_var.set("Resumed ▶️")

        self.update_display(self.engine.get_active())

    def finish_focus(self):
        active = self.engine.get_active()
        if not active:
            return

        if active.get("session_type") == "focus":
            next_session = self.engine.complete_focus(active)
            if next_session:
                self.status_var.set("Focus finished early. Break started.")
            else:
                self.status_var.set("Focus finished early.")
            self.update_display(self.engine.get_active())

    def skip_break(self):
        active = self.engine.get_active()
        if active and active.get("session_type") == "break":
            self.engine.complete_break(active)
            self.status_var.set("Break skipped ⏭")
            self.update_display(self.engine.get_active())

    def update_display(self, active):
        if not active:
            self._set_idle_display()
            return

        remaining = active.get("remaining_seconds", 0)
        total = max(active.get("total_seconds", 1), 1)
        progress = int(100 * (1 - remaining / total))
        progress = max(0, min(progress, 100))

        mins, secs = divmod(max(remaining, 0), 60)
        self.timer_var.set(f"{mins:02d}:{secs:02d}")

        session_type = active.get("session_type")
        cycle = self._display_cycle(active)
        subject = active.get("subject", "")

        if session_type == "focus":
            self.mode_var.set(f"FOCUS • Cycle {cycle} 🍅")
            task_name = active.get("task") or "No task"
            self.subtitle_var.set(f"{subject} • {task_name}")
        else:
            self.mode_var.set(f"BREAK ☕ • Cycle {cycle}")
            self.subtitle_var.set(subject)

        self.progress_bar["value"] = progress
        self.progress_var.set(f"{progress}%")

    # ─────────────────────────────────────
    # MAIN TICK LOOP
    # ─────────────────────────────────────
    def tick_loop(self):
        active = self.engine.tick()
        self.update_display(active)
        self.root.after(1000, self.tick_loop)

    # ─────────────────────────────────────
    # RUN APP
    # ─────────────────────────────────────
    def run(self):
        self.root.mainloop()
