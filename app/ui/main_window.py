import tkinter as tk
from tkinter import ttk

from app.ui.panels import DashboardPanel, FocusPanel, PlannerPanel, TasksPanel
from app.ui.theme import configure_styles


WINDOW_SIZE = "1080x760"


class MainWindow:
    def __init__(self, session_engine, task_manager):
        self.engine = session_engine
        self.task_manager = task_manager

        self.root = tk.Tk()
        self.root.title("Pomodoro Syllabus")
        self.root.geometry(WINDOW_SIZE)
        self.root.minsize(980, 680)

        configure_styles(self.root)

        self.status_var = tk.StringVar(value="Ready to focus.")
        self._active_context = None

        self._build_shell()
        self.refresh_views()
        self.tick_loop()

    def _build_shell(self):
        header = ttk.Frame(self.root, style="Card.TFrame", padding=18)
        header.pack(fill="x", padx=18, pady=(18, 10))
        ttk.Label(header, text="Pomodoro Syllabus", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="A cleaner study cockpit with separate flows for focus, tasks, planning, and review.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(6, 0))

        self.notebook = ttk.Notebook(self.root, style="App.TNotebook")
        self.notebook.pack(fill="both", expand=True, padx=18, pady=(0, 10))

        self.focus_panel = FocusPanel(
            self.notebook,
            self.engine,
            self.task_manager,
            on_status=self.set_status,
            on_data_changed=self.refresh_views,
        )
        self.tasks_panel = TasksPanel(
            self.notebook,
            self.task_manager,
            on_status=self.set_status,
            on_data_changed=self.refresh_views,
        )
        self.planner_panel = PlannerPanel(self.notebook, self.task_manager)
        self.dashboard_panel = DashboardPanel(self.notebook, self.task_manager)

        self.notebook.add(self.focus_panel.frame, text="Focus")
        self.notebook.add(self.tasks_panel.frame, text="Tasks")
        self.notebook.add(self.planner_panel.frame, text="Planner")
        self.notebook.add(self.dashboard_panel.frame, text="Dashboard")

        status_bar = ttk.Frame(self.root, style="Card.TFrame", padding=(18, 12))
        status_bar.pack(fill="x", padx=18, pady=(0, 18))
        ttk.Label(status_bar, textvariable=self.status_var, style="Body.TLabel").pack(anchor="w")

    def set_status(self, message):
        self.status_var.set(message)

    def _current_context(self, active):
        if not active:
            return None
        return (
            active.get("session_type"),
            active.get("state"),
            active.get("cycle_count"),
            active.get("task_id"),
            active.get("subject"),
        )

    def refresh_views(self):
        active = self.engine.get_active()
        self.focus_panel.refresh_task_choices()
        self.focus_panel.update_display(active)
        self.tasks_panel.refresh()
        self.planner_panel.refresh()
        self.dashboard_panel.refresh()
        self._active_context = self._current_context(active)

    def tick_loop(self):
        active = self.engine.tick()
        context = self._current_context(active)

        if context != self._active_context:
            self.refresh_views()
        else:
            self.focus_panel.update_display(active)
            self.dashboard_panel.refresh()

        self.root.after(1000, self.tick_loop)

    def run(self):
        self.root.mainloop()
