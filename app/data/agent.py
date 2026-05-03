from app.core.session_engine import SessionEngine
from app.core.taskmanager import TaskManager


class Agent:
    def __init__(self, session_engine: SessionEngine, task_manager: TaskManager):
        self.session = session_engine
        self.tasks = task_manager

    def handle_command(self, command, **kwargs):
        if command == "start_focus":
            return self.session.start_focus(subject="General", minutes=25)

        if command == "list_tasks":
            return self.tasks.list_tasks(**kwargs)
