import sys
from pathlib import Path

# Allow direct execution via `python3 app/__main__.py` as well as `python3 -m app`.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core import SessionEngine, TaskManager
from app.data import Storage
from app.ui import MainWindow


def main():
    storage = Storage()
    task_manager = TaskManager(storage)
    engine = SessionEngine(storage)
    MainWindow(engine, task_manager).run()


if __name__ == "__main__":
    main()
