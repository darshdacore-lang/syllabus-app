from tkinter import ttk


class PlannerPanel:
    def __init__(self, parent, task_manager):
        self.task_manager = task_manager
        self.frame = ttk.Frame(parent, style="App.TFrame", padding=18)
        self._build()
        self.refresh()

    def _build(self):
        self.frame.columnconfigure(0, weight=1)
        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(1, weight=1)

        header = ttk.Frame(self.frame, style="Card.TFrame", padding=18)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        ttk.Label(header, text="Planner Snapshot", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="This tab turns your saved plans, exams, and topic progress into one clean planning view.",
            style="Muted.TLabel",
            wraplength=760,
        ).pack(anchor="w", pady=(6, 0))

        self.plan_tree = self._build_tree(
            row=1,
            column=0,
            title="Study Plans",
            columns=("subject", "schedule", "time", "minutes"),
            headings=("Subject", "Schedule", "Time", "Minutes"),
        )
        self.exam_tree = self._build_tree(
            row=1,
            column=1,
            title="Upcoming Exams",
            columns=("name", "subject", "date", "countdown"),
            headings=("Exam", "Subject", "Date", "Countdown"),
        )
        self.topic_tree = self._build_tree(
            row=2,
            column=0,
            title="Topic Progress",
            columns=("subject", "topic", "progress"),
            headings=("Subject", "Topic", "Progress"),
            columnspan=2,
        )

    def _build_tree(self, row, column, title, columns, headings, columnspan=1):
        card = ttk.LabelFrame(
            self.frame,
            text=title,
            style="Section.TLabelframe",
            padding=16,
        )
        card.grid(row=row, column=column, columnspan=columnspan, sticky="nsew", padx=(0, 12) if column == 0 else 0, pady=(0, 12))
        card.columnconfigure(0, weight=1)
        card.rowconfigure(0, weight=1)

        tree = ttk.Treeview(card, columns=columns, show="headings", height=8)
        for name, heading in zip(columns, headings):
            tree.heading(name, text=heading)
            tree.column(name, width=150, anchor="w")
        tree.grid(row=0, column=0, sticky="nsew")
        return tree

    def refresh(self):
        snapshot = self.task_manager.planner_snapshot()
        self._populate(
            self.plan_tree,
            snapshot["plans"],
            lambda plan: (
                plan["subject"],
                plan["schedule"],
                plan["time"],
                f"{plan['minutes']} min",
            ),
            fallback=("No plans yet", "-", "-", "-"),
        )
        self._populate(
            self.exam_tree,
            snapshot["exams"],
            lambda exam: (
                exam["name"],
                exam["subject"],
                exam["date"] or "-",
                exam["countdown"],
            ),
            fallback=("No exams yet", "-", "-", "-"),
        )
        self._populate(
            self.topic_tree,
            snapshot["topics"],
            lambda topic: (
                topic["subject"],
                topic["topic"],
                f"{topic['progress']}%",
            ),
            fallback=("No topics yet", "-", "-"),
        )

    def _populate(self, tree, rows, row_builder, fallback):
        for item in tree.get_children():
            tree.delete(item)

        if not rows:
            tree.insert("", "end", values=fallback)
            return

        for row in rows:
            tree.insert("", "end", values=row_builder(row))
