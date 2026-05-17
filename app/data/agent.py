import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.session_engine import SessionEngine
from app.core.taskmanager import TaskManager


class Agent:
    """
    Command-based agent that exposes session and task management functionality.
    Provides a unified interface for controlling focus sessions, task lifecycle,
    and retrieving summaries.
    """

    def __init__(self, session_engine: SessionEngine, task_manager: TaskManager):
        self.session = session_engine
        self.tasks = task_manager
        self._register_commands()

    def _register_commands(self):
        """Register all available commands."""
        self.commands = {
            # Session controls
            "get_active": self._cmd_get_active,
            "start_focus": self._cmd_start_focus,
            "pause": self._cmd_pause,
            "resume": self._cmd_resume,
            "tick": self._cmd_tick,
            "next_break_preview": self._cmd_next_break_preview,
            # Task lifecycle
            "add_task": self._cmd_add_task,
            "list_tasks": self._cmd_list_tasks,
            "mark_done": self._cmd_mark_done,
            "delete_task": self._cmd_delete_task,
            "get_sorted_tasks": self._cmd_get_sorted_tasks,
            # Smart commands
            "suggest_next_task": self._cmd_suggest_next_task,
            "start_task_focus": self._cmd_start_task_focus,
            # Summary commands
            "dashboard_summary": self._cmd_dashboard_summary,
            "planner_snapshot": self._cmd_planner_snapshot,
            # Utility
            "help": self._cmd_help,
            "list_commands": self._cmd_list_commands,
        }

    def handle_command(self, command, **kwargs):
        """
        Route command to appropriate handler.

        Args:
            command: The command name
            **kwargs: Arguments to pass to the command handler

        Returns:
            The result from the command handler

        Raises:
            ValueError: If the command is unknown
        """
        if command not in self.commands:
            raise ValueError(
                f"Unknown command: '{command}'. Use 'list_commands' or 'help' for available commands."
            )
        return self.commands[command](**kwargs)

    # ─────────────────────────────
    # SESSION CONTROLS
    # ─────────────────────────────
    def _cmd_get_active(self, **kwargs):
        """Get the currently active session (focus or break)."""
        return self.session.get_active()

    def _cmd_start_focus(
        self,
        subject="General",
        minutes=25,
        task=None,
        task_id=None,
        tags=None,
        break_plan=None,
        **kwargs,
    ):
        """
        Start a focus session with customizable parameters.

        Args:
            subject: Study subject (default: "General")
            minutes: Duration in minutes (default: 25)
            task: Task description/title (optional)
            task_id: Associated task ID (optional)
            tags: List of tags for session (optional)
            break_plan: Custom break configuration (optional)
        """
        return self.session.start_focus(
            subject=subject,
            minutes=minutes,
            task=task,
            task_id=task_id,
            tags=tags,
            break_plan=break_plan,
        )

    def _cmd_pause(self, **kwargs):
        """Pause the active focus session."""
        self.session.pause()
        return self.session.get_active()

    def _cmd_resume(self, **kwargs):
        """Resume a paused focus session."""
        self.session.resume()
        return self.session.get_active()

    def _cmd_tick(self, **kwargs):
        """Advance the active session by elapsed time (called by timer)."""
        return self.session.tick()

    def _cmd_next_break_preview(self, **kwargs):
        """Preview what the next break will be after current focus session."""
        return self.session.next_break_preview()

    # ─────────────────────────────
    # TASK LIFECYCLE
    # ─────────────────────────────
    def _cmd_add_task(
        self, title, subject="General", due_date="", tags=None, details="", **kwargs
    ):
        """
        Create a new task.

        Args:
            title: Task title (required)
            subject: Subject/course (default: "General")
            due_date: Due date (optional)
            tags: List of tags (optional)
            details: Task description (optional)
        """
        return self.tasks.add_task(
            title=title,
            subject=subject,
            due_date=due_date,
            tags=tags,
            details=details,
        )

    def _cmd_list_tasks(self, include_done=False, **kwargs):
        """
        List all tasks, optionally including completed ones.

        Args:
            include_done: Include completed tasks (default: False)
        """
        return self.tasks.list_tasks(include_done=include_done)

    def _cmd_mark_done(self, task_id, **kwargs):
        """
        Mark a task as complete.

        Args:
            task_id: ID of task to mark done
        """
        return self.tasks.mark_done(task_id)

    def _cmd_delete_task(self, task_id, **kwargs):
        """
        Delete a task.

        Args:
            task_id: ID of task to delete
        """
        self.tasks.delete_task(task_id)
        return {"status": "deleted", "task_id": task_id}

    def _cmd_get_sorted_tasks(self, **kwargs):
        """
        Get all open tasks sorted by priority (due date, subject importance, etc).
        """
        return self.tasks.get_sorted_tasks()

    # ─────────────────────────────
    # SMART COMMANDS
    # ─────────────────────────────
    def _cmd_suggest_next_task(self, **kwargs):
        """
        Suggest the highest-priority task to work on next.
        Uses priority_score which considers due dates, time investment, and subject goals.
        """
        sorted_tasks = self.tasks.get_sorted_tasks()
        if not sorted_tasks:
            return None
        return sorted_tasks[0]

    def _cmd_start_task_focus(self, task_id, minutes=25, break_plan=None, **kwargs):
        """
        Start a focus session with subject and task details from a task ID.

        Args:
            task_id: ID of the task to focus on
            minutes: Duration in minutes (default: 25)
            break_plan: Custom break configuration (optional)
        """
        defaults = self.tasks.get_focus_defaults(task_id)
        return self.session.start_focus(
            subject=defaults.get("subject", "General"),
            minutes=minutes,
            task=defaults.get("task_title", ""),
            task_id=task_id,
            tags=defaults.get("tags", []),
            break_plan=break_plan,
        )

    # ─────────────────────────────
    # SUMMARY COMMANDS
    # ─────────────────────────────
    def _cmd_dashboard_summary(self, **kwargs):
        """
        Get dashboard summary: today's stats, recent sessions, upcoming exams, etc.
        """
        return self.tasks.dashboard_summary()

    def _cmd_planner_snapshot(self, **kwargs):
        """
        Get planner snapshot: active plans, exams, and topics.
        """
        return self.tasks.planner_snapshot()

    # ─────────────────────────────
    # UTILITY COMMANDS
    # ─────────────────────────────
    def _cmd_help(self, command=None, **kwargs):
        """
        Get help on a specific command or all commands.

        Args:
            command: Specific command to get help for (optional)
        """
        if command and command in self.commands:
            handler = self.commands[command]
            docstring = handler.__doc__ or "No documentation available."
            return {
                "command": command,
                "help": docstring.strip(),
            }

        help_text = {
            "description": "Session and task management agent with command routing",
            "usage": "agent.handle_command(command_name, **kwargs)",
            "categories": {
                "Session Controls": [
                    "get_active - Get currently active session",
                    "start_focus - Start a focus session with custom parameters",
                    "pause - Pause the active session",
                    "resume - Resume a paused session",
                    "tick - Advance timer (called by UI)",
                    "next_break_preview - See what break comes next",
                ],
                "Task Lifecycle": [
                    "add_task - Create a new task",
                    "list_tasks - List open tasks",
                    "mark_done - Mark a task complete",
                    "delete_task - Delete a task",
                    "get_sorted_tasks - Get tasks by priority",
                ],
                "Smart Commands": [
                    "suggest_next_task - Recommend task with highest priority",
                    "start_task_focus - Focus on a specific task",
                ],
                "Summaries": [
                    "dashboard_summary - Today's stats and recent activity",
                    "planner_snapshot - Plans, exams, and topics",
                ],
                "Utility": [
                    "help [command] - Show this help or help for a command",
                    "list_commands - List all available commands",
                ],
            },
        }
        return help_text

    def _cmd_list_commands(self, **kwargs):
        """List all available commands."""
        return sorted(list(self.commands.keys()))
