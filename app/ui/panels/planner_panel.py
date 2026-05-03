import tkinter as tk
from tkinter import messagebox, ttk

from app.utils.helpers import parse_date, safe_int


class PlannerPanel:
    def __init__(self, parent, task_manager, on_status, on_data_changed):
        self.task_manager = task_manager
        self.on_status = on_status
        self.on_data_changed = on_data_changed
        self.frame = ttk.Frame(parent, style="App.TFrame", padding=18)

        self.plan_id = None
        self.exam_id = None
        self.topic_id = None

        self.plan_subject_var = tk.StringVar(value="General")
        self.plan_days_var = tk.StringVar()
        self.plan_time_var = tk.StringVar()
        self.plan_minutes_var = tk.StringVar(value="45")
        self.plan_notes_var = tk.StringVar()

        self.exam_name_var = tk.StringVar()
        self.exam_subject_var = tk.StringVar(value="General")
        self.exam_date_var = tk.StringVar()
        self.exam_target_minutes_var = tk.StringVar(value="180")
        self.exam_notes_var = tk.StringVar()

        self.topic_subject_var = tk.StringVar(value="General")
        self.topic_name_var = tk.StringVar()
        self.topic_progress_var = tk.StringVar(value="0")
        self.topic_notes_var = tk.StringVar()

        self._build()
        self.refresh()

    def _build(self):
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        header = ttk.Frame(self.frame, style="Card.TFrame", padding=18)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(header, text="Planner Studio", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Plans, exams, and topics are editable here so your study structure lives inside the app instead of the JSON file.",
            style="Muted.TLabel",
            wraplength=840,
        ).pack(anchor="w", pady=(6, 0))

        self.notebook = ttk.Notebook(self.frame, style="App.TNotebook")
        self.notebook.grid(row=1, column=0, sticky="nsew")

        plan_tab = ttk.Frame(self.notebook, style="App.TFrame", padding=8)
        exam_tab = ttk.Frame(self.notebook, style="App.TFrame", padding=8)
        topic_tab = ttk.Frame(self.notebook, style="App.TFrame", padding=8)
        self.notebook.add(plan_tab, text="Plans")
        self.notebook.add(exam_tab, text="Exams")
        self.notebook.add(topic_tab, text="Topics")

        self.plan_tree = self._build_editor_tab(
            plan_tab,
            title="Study Plans",
            form_builder=self._build_plan_form,
            columns=("subject", "schedule", "time", "minutes"),
            headings=("Subject", "Schedule", "Time", "Minutes"),
            width_map={"subject": 160, "schedule": 200, "time": 100, "minutes": 90},
        )
        self.exam_tree = self._build_editor_tab(
            exam_tab,
            title="Exams",
            form_builder=self._build_exam_form,
            columns=("name", "subject", "date", "countdown"),
            headings=("Exam", "Subject", "Date", "Countdown"),
            width_map={"name": 200, "subject": 140, "date": 120, "countdown": 140},
        )
        self.topic_tree = self._build_editor_tab(
            topic_tab,
            title="Topics",
            form_builder=self._build_topic_form,
            columns=("subject", "topic", "progress"),
            headings=("Subject", "Topic", "Progress"),
            width_map={"subject": 160, "topic": 240, "progress": 100},
        )

    def _build_editor_tab(self, parent, title, form_builder, columns, headings, width_map):
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(0, weight=1)

        composer = ttk.LabelFrame(parent, text=title, style="Section.TLabelframe", padding=16)
        composer.grid(row=0, column=0, sticky="nsw", padx=(0, 12))
        composer.columnconfigure(0, weight=1)
        form_builder(composer)

        board = ttk.LabelFrame(parent, text=f"{title} Board", style="Section.TLabelframe", padding=16)
        board.grid(row=0, column=1, sticky="nsew")
        board.columnconfigure(0, weight=1)
        board.rowconfigure(0, weight=1)

        tree = ttk.Treeview(board, columns=columns, show="headings", height=14)
        for column, heading in zip(columns, headings):
            tree.heading(column, text=heading)
            tree.column(column, width=width_map[column], anchor="w")
        tree.grid(row=0, column=0, sticky="nsew")
        return tree

    def _build_plan_form(self, frame):
        ttk.Label(frame, text="Subject", style="Body.TLabel").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.plan_subject_var).grid(row=1, column=0, sticky="ew", pady=4)
        ttk.Label(frame, text="Days (comma-separated)", style="Body.TLabel").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.plan_days_var).grid(row=3, column=0, sticky="ew", pady=4)
        ttk.Label(frame, text="Time", style="Body.TLabel").grid(row=4, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.plan_time_var).grid(row=5, column=0, sticky="ew", pady=4)
        ttk.Label(frame, text="Minutes", style="Body.TLabel").grid(row=6, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.plan_minutes_var).grid(row=7, column=0, sticky="ew", pady=4)
        ttk.Label(frame, text="Notes", style="Body.TLabel").grid(row=8, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.plan_notes_var).grid(row=9, column=0, sticky="ew", pady=4)
        ttk.Button(frame, text="Save Plan", style="Accent.TButton", command=self.save_plan).grid(
            row=10, column=0, sticky="ew", pady=(12, 4)
        )
        action_row = ttk.Frame(frame, style="Card.TFrame")
        action_row.grid(row=11, column=0, sticky="ew", pady=(4, 0))
        ttk.Button(action_row, text="Clear", style="Subtle.TButton", command=self.clear_plan_form).pack(side="left", padx=(0, 8))
        ttk.Button(action_row, text="Delete Selected", style="Subtle.TButton", command=self.delete_plan).pack(side="left")
        ttk.Label(
            frame,
            text="Tip: days can be like Mon, Wed, Fri and time can stay blank if you only want a loose plan.",
            style="Muted.TLabel",
            wraplength=240,
        ).grid(row=12, column=0, sticky="w", pady=(10, 0))

    def _build_exam_form(self, frame):
        ttk.Label(frame, text="Exam Name", style="Body.TLabel").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.exam_name_var).grid(row=1, column=0, sticky="ew", pady=4)
        ttk.Label(frame, text="Subject", style="Body.TLabel").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.exam_subject_var).grid(row=3, column=0, sticky="ew", pady=4)
        ttk.Label(frame, text="Date (YYYY-MM-DD)", style="Body.TLabel").grid(row=4, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.exam_date_var).grid(row=5, column=0, sticky="ew", pady=4)
        ttk.Label(frame, text="Target Minutes", style="Body.TLabel").grid(row=6, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.exam_target_minutes_var).grid(row=7, column=0, sticky="ew", pady=4)
        ttk.Label(frame, text="Notes", style="Body.TLabel").grid(row=8, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.exam_notes_var).grid(row=9, column=0, sticky="ew", pady=4)
        ttk.Button(frame, text="Save Exam", style="Accent.TButton", command=self.save_exam).grid(
            row=10, column=0, sticky="ew", pady=(12, 4)
        )
        action_row = ttk.Frame(frame, style="Card.TFrame")
        action_row.grid(row=11, column=0, sticky="ew", pady=(4, 0))
        ttk.Button(action_row, text="Clear", style="Subtle.TButton", command=self.clear_exam_form).pack(side="left", padx=(0, 8))
        ttk.Button(action_row, text="Delete Selected", style="Subtle.TButton", command=self.delete_exam).pack(side="left")

    def _build_topic_form(self, frame):
        ttk.Label(frame, text="Subject", style="Body.TLabel").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.topic_subject_var).grid(row=1, column=0, sticky="ew", pady=4)
        ttk.Label(frame, text="Topic", style="Body.TLabel").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.topic_name_var).grid(row=3, column=0, sticky="ew", pady=4)
        ttk.Label(frame, text="Progress %", style="Body.TLabel").grid(row=4, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.topic_progress_var).grid(row=5, column=0, sticky="ew", pady=4)
        ttk.Label(frame, text="Notes", style="Body.TLabel").grid(row=6, column=0, sticky="w", pady=4)
        ttk.Entry(frame, textvariable=self.topic_notes_var).grid(row=7, column=0, sticky="ew", pady=4)
        ttk.Button(frame, text="Save Topic", style="Accent.TButton", command=self.save_topic).grid(
            row=8, column=0, sticky="ew", pady=(12, 4)
        )
        action_row = ttk.Frame(frame, style="Card.TFrame")
        action_row.grid(row=9, column=0, sticky="ew", pady=(4, 0))
        ttk.Button(action_row, text="Clear", style="Subtle.TButton", command=self.clear_topic_form).pack(side="left", padx=(0, 8))
        ttk.Button(action_row, text="Delete Selected", style="Subtle.TButton", command=self.delete_topic).pack(side="left")

    def refresh(self):
        snapshot = self.task_manager.planner_snapshot()
        self._populate_plans(snapshot["plans"])
        self._populate_exams(snapshot["exams"])
        self._populate_topics(snapshot["topics"])

    def _populate_plans(self, plans):
        self._clear_tree(self.plan_tree)
        for plan in plans:
            self.plan_tree.insert(
                "",
                "end",
                iid=str(plan["id"]),
                values=(plan["subject"], plan["schedule"], plan["time"], f"{plan['minutes']} min"),
            )
        self.plan_tree.bind("<<TreeviewSelect>>", self.load_selected_plan)

    def _populate_exams(self, exams):
        self._clear_tree(self.exam_tree)
        for exam in exams:
            self.exam_tree.insert(
                "",
                "end",
                iid=str(exam["id"]),
                values=(exam["name"], exam["subject"], exam["date"] or "-", exam["countdown"]),
            )
        self.exam_tree.bind("<<TreeviewSelect>>", self.load_selected_exam)

    def _populate_topics(self, topics):
        self._clear_tree(self.topic_tree)
        for topic in topics:
            self.topic_tree.insert(
                "",
                "end",
                iid=str(topic["id"]),
                values=(topic["subject"], topic["topic"], f"{topic['progress']}%"),
            )
        self.topic_tree.bind("<<TreeviewSelect>>", self.load_selected_topic)

    def _clear_tree(self, tree):
        for item in tree.get_children():
            tree.delete(item)

    def save_plan(self):
        record = self.task_manager.save_plan(
            plan_id=self.plan_id,
            subject=self.plan_subject_var.get(),
            days=self.plan_days_var.get(),
            time=self.plan_time_var.get(),
            minutes=self.plan_minutes_var.get(),
            notes=self.plan_notes_var.get(),
        )
        self.plan_id = record["id"]
        self.on_status(f"Plan saved for {record['subject']}.")
        self.on_data_changed()
        self.refresh()

    def delete_plan(self):
        if not self.plan_id:
            self.on_status("Select a plan first.")
            return
        self.task_manager.delete_plan(self.plan_id)
        self.clear_plan_form()
        self.on_status("Plan deleted.")
        self.on_data_changed()
        self.refresh()

    def clear_plan_form(self):
        self.plan_id = None
        self.plan_subject_var.set("General")
        self.plan_days_var.set("")
        self.plan_time_var.set("")
        self.plan_minutes_var.set("45")
        self.plan_notes_var.set("")

    def load_selected_plan(self, _event=None):
        selection = self.plan_tree.selection()
        if not selection:
            return
        plan_id = int(selection[0])
        for plan in self.task_manager.planner_snapshot()["plans"]:
            if plan["id"] != plan_id:
                continue
            self.plan_id = plan_id
            self.plan_subject_var.set(plan["subject"])
            self.plan_days_var.set(", ".join(plan["days"]))
            self.plan_time_var.set(plan["time"] if plan["time"] != "--:--" else "")
            self.plan_minutes_var.set(str(plan["minutes"]))
            self.plan_notes_var.set(plan["notes"])
            break

    def save_exam(self):
        if self.exam_date_var.get().strip() and parse_date(self.exam_date_var.get().strip()) is None:
            messagebox.showerror("Invalid exam date", "Use YYYY-MM-DD for exam dates.")
            return

        record = self.task_manager.save_exam(
            exam_id=self.exam_id,
            name=self.exam_name_var.get(),
            subject=self.exam_subject_var.get(),
            date=self.exam_date_var.get(),
            target_minutes=self.exam_target_minutes_var.get(),
            notes=self.exam_notes_var.get(),
        )
        self.exam_id = record["id"]
        self.on_status(f"Exam saved: {record['name']}.")
        self.on_data_changed()
        self.refresh()

    def delete_exam(self):
        if not self.exam_id:
            self.on_status("Select an exam first.")
            return
        self.task_manager.delete_exam(self.exam_id)
        self.clear_exam_form()
        self.on_status("Exam deleted.")
        self.on_data_changed()
        self.refresh()

    def clear_exam_form(self):
        self.exam_id = None
        self.exam_name_var.set("")
        self.exam_subject_var.set("General")
        self.exam_date_var.set("")
        self.exam_target_minutes_var.set("180")
        self.exam_notes_var.set("")

    def load_selected_exam(self, _event=None):
        selection = self.exam_tree.selection()
        if not selection:
            return
        exam_id = int(selection[0])
        for exam in self.task_manager.planner_snapshot()["exams"]:
            if exam["id"] != exam_id:
                continue
            self.exam_id = exam_id
            self.exam_name_var.set(exam["name"])
            self.exam_subject_var.set(exam["subject"])
            self.exam_date_var.set(exam["date"])
            self.exam_target_minutes_var.set(str(exam["target_minutes"]))
            self.exam_notes_var.set(exam["notes"])
            break

    def save_topic(self):
        progress = safe_int(self.topic_progress_var.get(), -1)
        if progress < 0 or progress > 100:
            messagebox.showerror("Invalid progress", "Topic progress must be between 0 and 100.")
            return

        record = self.task_manager.save_topic(
            topic_id=self.topic_id,
            subject=self.topic_subject_var.get(),
            topic=self.topic_name_var.get(),
            progress=progress,
            notes=self.topic_notes_var.get(),
        )
        self.topic_id = record["id"]
        self.on_status(f"Topic saved: {record['topic']}.")
        self.on_data_changed()
        self.refresh()

    def delete_topic(self):
        if not self.topic_id:
            self.on_status("Select a topic first.")
            return
        self.task_manager.delete_topic(self.topic_id)
        self.clear_topic_form()
        self.on_status("Topic deleted.")
        self.on_data_changed()
        self.refresh()

    def clear_topic_form(self):
        self.topic_id = None
        self.topic_subject_var.set("General")
        self.topic_name_var.set("")
        self.topic_progress_var.set("0")
        self.topic_notes_var.set("")

    def load_selected_topic(self, _event=None):
        selection = self.topic_tree.selection()
        if not selection:
            return
        topic_id = int(selection[0])
        for topic in self.task_manager.planner_snapshot()["topics"]:
            if topic["id"] != topic_id:
                continue
            self.topic_id = topic_id
            self.topic_subject_var.set(topic["subject"])
            self.topic_name_var.set(topic["topic"])
            self.topic_progress_var.set(str(topic["progress"]))
            self.topic_notes_var.set(topic["notes"])
            break
