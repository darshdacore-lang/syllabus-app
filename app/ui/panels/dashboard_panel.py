import sys
from pathlib import Path

from tkinter import ttk

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.utils.helpers import format_minutes


class DashboardPanel:
    def __init__(self, parent, agent, task_manager):
        self.agent = agent
        self.task_manager = task_manager
        self.frame = ttk.Frame(parent, style="App.TFrame", padding=18)
        self.metric_vars = {}
        self._build()
        self.refresh()

    def _build(self):
        self.frame.columnconfigure(0, weight=1)
        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(2, weight=1)

        header = ttk.Frame(self.frame, style="Card.TFrame", padding=18)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        ttk.Label(header, text="Study Dashboard", style="Title.TLabel").pack(anchor="w")
        self.headline_var = ttk.Label(header, text="", style="Body.TLabel")
        self.headline_var.pack(anchor="w", pady=(6, 0))
        self.next_exam_var = ttk.Label(header, text="", style="Muted.TLabel")
        self.next_exam_var.pack(anchor="w", pady=(6, 0))

        metric_row = ttk.Frame(self.frame, style="App.TFrame")
        metric_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        for column in range(4):
            metric_row.columnconfigure(column, weight=1)

        for index, (key, label) in enumerate(
            (
                ("today_minutes", "Today"),
                ("today_sessions", "Sessions Today"),
                ("open_tasks", "Open Tasks"),
                ("total_minutes", "All-Time Minutes"),
            )
        ):
            card = ttk.Frame(metric_row, style="Card.TFrame", padding=16)
            card.grid(
                row=0, column=index, sticky="nsew", padx=(0, 10) if index < 3 else 0
            )
            self.metric_vars[key] = ttk.Label(
                card, text="0", style="MetricValue.TLabel"
            )
            self.metric_vars[key].pack(anchor="w")
            ttk.Label(card, text=label, style="MetricLabel.TLabel").pack(
                anchor="w", pady=(4, 0)
            )

        recent_card = ttk.LabelFrame(
            self.frame,
            text="Recent Sessions",
            style="Section.TLabelframe",
            padding=16,
        )
        recent_card.grid(row=2, column=0, sticky="nsew", padx=(0, 12))
        recent_card.columnconfigure(0, weight=1)
        recent_card.rowconfigure(0, weight=1)
        self.recent_tree = ttk.Treeview(
            recent_card,
            columns=("subject", "task", "minutes"),
            show="headings",
            height=10,
        )
        for column, heading, width in (
            ("subject", "Subject", 140),
            ("task", "Task", 220),
            ("minutes", "Minutes", 90),
        ):
            self.recent_tree.heading(column, text=heading)
            self.recent_tree.column(column, width=width, anchor="w")
        self.recent_tree.grid(row=0, column=0, sticky="nsew")

        subject_card = ttk.LabelFrame(
            self.frame,
            text="Top Subjects",
            style="Section.TLabelframe",
            padding=16,
        )
        subject_card.grid(row=2, column=1, sticky="nsew")
        subject_card.columnconfigure(0, weight=1)
        subject_card.rowconfigure(0, weight=1)
        self.subject_tree = ttk.Treeview(
            subject_card,
            columns=("subject", "minutes"),
            show="headings",
            height=10,
        )
        self.subject_tree.heading("subject", text="Subject")
        self.subject_tree.heading("minutes", text="Minutes")
        self.subject_tree.column("subject", width=180, anchor="w")
        self.subject_tree.column("minutes", width=100, anchor="w")
        self.subject_tree.grid(row=0, column=0, sticky="nsew")

    def refresh(self):
        summary = self.agent.handle_command("dashboard_summary")
        self.metric_vars["today_minutes"].configure(
            text=format_minutes(summary["today_minutes"])
        )
        self.metric_vars["today_sessions"].configure(
            text=str(summary["today_sessions"])
        )
        self.metric_vars["open_tasks"].configure(text=str(summary["open_tasks"]))
        self.metric_vars["total_minutes"].configure(
            text=str(int(summary["total_minutes"]))
        )
        self.headline_var.configure(text=summary["headline"])

        next_exam = summary["next_exam"]
        if next_exam:
            self.next_exam_var.configure(
                text=f"Next exam: {next_exam['name']} ({next_exam['subject']}) - {next_exam['countdown']}"
            )
        else:
            self.next_exam_var.configure(text="No upcoming exams recorded yet.")

        self._populate_recent(summary["recent_sessions"])
        self._populate_subjects(summary["top_subjects"])

    def _populate_recent(self, sessions):
        for item in self.recent_tree.get_children():
            self.recent_tree.delete(item)

        if not sessions:
            self.recent_tree.insert("", "end", values=("No sessions yet", "-", "-"))
            return

        for session in sessions:
            self.recent_tree.insert(
                "",
                "end",
                values=(
                    session["subject"],
                    session["task"],
                    format_minutes(session["minutes"]),
                ),
            )

    def _populate_subjects(self, subjects):
        for item in self.subject_tree.get_children():
            self.subject_tree.delete(item)

        if not subjects:
            self.subject_tree.insert("", "end", values=("No study data yet", "-"))
            return

        for subject, minutes in subjects:
            self.subject_tree.insert(
                "", "end", values=(subject, format_minutes(minutes))
            )
