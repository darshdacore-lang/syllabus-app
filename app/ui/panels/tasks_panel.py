import tkinter as tk
from tkinter import messagebox, ttk

from app.utils.helpers import format_minutes, parse_date


class TasksPanel:
    def __init__(self, parent, task_manager, on_status, on_data_changed):
        self.task_manager = task_manager
        self.on_status = on_status
        self.on_data_changed = on_data_changed
        self.frame = ttk.Frame(parent, style="App.TFrame", padding=18)

        self.title_var = tk.StringVar()
        self.subject_var = tk.StringVar(value="General")
        self.due_date_var = tk.StringVar()
        self.tags_var = tk.StringVar()
        self.details_var = tk.StringVar()

        self._build()
        self.refresh()

    def _build(self):
        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(1, weight=1)
        self.status_filter = tk.StringVar(value="open")

        composer = ttk.LabelFrame(
            self.frame,
            text="Quick Task Add",
            style="Section.TLabelframe",
            padding=14,
        )
        composer.grid(row=0, column=0, sticky="nsw", padx=(0, 12))
        composer.columnconfigure(0, weight=1)

        ttk.Label(composer, text="Title", style="Body.TLabel").grid(
            row=0, column=0, sticky="w", pady=4
        )
        ttk.Entry(composer, textvariable=self.title_var, width=24).grid(
            row=1, column=0, sticky="ew", pady=4
        )

        ttk.Label(composer, text="Subject", style="Body.TLabel").grid(
            row=2, column=0, sticky="w", pady=4
        )
        ttk.Entry(composer, textvariable=self.subject_var, width=24).grid(
            row=3, column=0, sticky="ew", pady=4
        )

        ttk.Label(composer, text="Due Date", style="Body.TLabel").grid(
            row=4, column=0, sticky="w", pady=4
        )
        ttk.Entry(composer, textvariable=self.due_date_var, width=24).grid(
            row=5, column=0, sticky="ew", pady=4
        )
        ttk.Label(composer, text="YYYY-MM-DD", style="Muted.TLabel").grid(
            row=6, column=0, sticky="w"
        )

        ttk.Label(composer, text="Tags", style="Body.TLabel").grid(
            row=7, column=0, sticky="w", pady=(12, 4)
        )
        ttk.Entry(composer, textvariable=self.tags_var, width=24).grid(
            row=8, column=0, sticky="ew", pady=4
        )

        ttk.Button(
            composer, text="Add Task", style="Accent.TButton", command=self.add_task
        ).grid(row=9, column=0, sticky="ew", pady=(12, 4))

        board = ttk.LabelFrame(
            self.frame,
            text="Tasks",
            style="Section.TLabelframe",
            padding=14,
        )
        board.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(0, 0))
        board.columnconfigure(0, weight=1)
        board.rowconfigure(1, weight=1)

        filter_bar = ttk.Frame(board, style="Card.TFrame")
        filter_bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(filter_bar, text="Show:", style="Body.TLabel").pack(
            side="left", padx=(0, 8)
        )

        for status_val, label in [("open", "Open"), ("done", "Done"), ("all", "All")]:
            ttk.Radiobutton(
                filter_bar,
                text=label,
                variable=self.status_filter,
                value=status_val,
                command=self.refresh,
            ).pack(side="left", padx=(0, 12))

        self.tree = ttk.Treeview(
            board,
            columns=("title", "subject", "due", "minutes"),
            show="headings",
            height=14,
        )
        for column, heading, width in (
            ("title", "Title", 240),
            ("subject", "Subject", 100),
            ("due", "Due", 90),
            ("minutes", "Time", 70),
        ):
            self.tree.heading(column, text=heading)
            self.tree.column(column, width=width, anchor="w")
        self.tree.grid(row=1, column=0, sticky="nsew")
        self.tree.bind("<Double-1>", self._on_tree_double_click)

        actions = ttk.Frame(board, style="Card.TFrame")
        actions.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(
            actions,
            text="✓ Mark Done",
            style="Success.TButton",
            command=lambda: self.set_selected_status("done"),
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            actions,
            text="↻ Reopen",
            style="Subtle.TButton",
            command=lambda: self.set_selected_status("open"),
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            actions,
            text="🗑 Delete",
            style="Subtle.TButton",
            command=self._delete_selected,
        ).pack(side="left")

    def _on_tree_double_click(self, event):
        """Edit task on double-click."""
        selection = self.tree.selection()
        if not selection:
            return
        task_id = int(selection[0])
        for task in self.task_manager.list_tasks(include_done=True):
            if task["id"] == task_id:
                self.title_var.set(task.get("title", ""))
                self.subject_var.set(task.get("subject", "General"))
                self.due_date_var.set(task.get("due_date", ""))
                self.tags_var.set(
                    ", ".join(task.get("tags", [])) if task.get("tags") else ""
                )
                self.on_status(
                    f"Editing: {task['title']} (delete and re-add to save changes)"
                )
                break

    def _delete_selected(self):
        task_id = self._selected_task_id()
        if task_id is None:
            self.on_status("Select a task first.")
            return
        try:
            self.task_manager.delete_task(task_id)
            self.on_status("Task deleted.")
            self.on_data_changed()
            self.refresh()
        except ValueError as exc:
            messagebox.showerror("Delete failed", str(exc))

    def add_task(self):
        title = self.title_var.get().strip()
        due_date = self.due_date_var.get().strip()
        if due_date and parse_date(due_date) is None:
            messagebox.showerror("Invalid due date", "Use YYYY-MM-DD for due dates.")
            return

        try:
            task = self.task_manager.add_task(
                title=title,
                subject=self.subject_var.get(),
                details=self.details_var.get(),
                due_date=due_date,
                tags=self.tags_var.get(),
            )
        except ValueError as exc:
            messagebox.showerror("Unable to add task", str(exc))
            return

        self.title_var.set("")
        self.due_date_var.set("")
        self.tags_var.set("")
        self.details_var.set("")
        self.on_status(f"Task added: {task['title']}")
        self.on_data_changed()
        self.refresh()

    def _selected_task_id(self):
        selection = self.tree.selection()
        if not selection:
            return None
        return int(selection[0])

    def set_selected_status(self, status):
        task_id = self._selected_task_id()
        if task_id is None:
            self.on_status("Select a task first.")
            return

        task = self.task_manager.set_task_status(task_id, status)
        self.on_status(f"Task updated: {task['title']} -> {status}")
        self.on_data_changed()
        self.refresh()

    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        filter_value = self.status_filter.get()
        tasks = self.task_manager.list_tasks(include_done=(filter_value != "open"))

        if filter_value == "open":
            tasks = [t for t in tasks if t.get("status") == "open"]
        elif filter_value == "done":
            tasks = [t for t in tasks if t.get("status") == "done"]

        if not tasks:
            self.tree.insert("", "end", values=("No tasks", "-", "-", "-"))
            return

        for task in tasks:
            due = task.get("due_date") or "-"
            self.tree.insert(
                "",
                "end",
                iid=str(task["id"]),
                values=(
                    task.get("title") or "-",
                    task.get("subject") or "General",
                    due,
                    format_minutes(task.get("minutes_logged", 0)),
                ),
            )
