import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.utils.helpers import safe_int, safe_float


class TaskManager:
    def __init__(self, storage):
        self.storage = storage
        self.profile = storage.profile

    def add_task(self, title, subject="General", due_date="", tags=None, details=""):
        title = (title or "").strip()
        if not title:
            raise ValueError("Task title cannot be empty.")
        task = {
            "id": self.storage.next_id("task"),
            "title": title,
            "subject": subject or "General",
            "due_date": due_date or "",
            "tags": tags.split(",") if isinstance(tags, str) else (tags or []),
            "details": details or "",
            "status": "open",
            "minutes_logged": 0,
        }
        self.profile.setdefault("tasks", []).append(task)
        self.storage.save()
        return task

    def get_tasks(self, status=None):
        tasks = self.profile.get("tasks", [])
        if status:
            return [t for t in tasks if t.get("status") == status]
        return tasks

    def list_tasks(self, include_done=False):
        tasks = self.get_tasks()
        if not include_done:
            tasks = [t for t in tasks if t.get("status") != "done"]
        return sorted(tasks, key=lambda t: t.get("title", ""))

    def set_task_status(self, task_id, status):
        task_id = safe_int(task_id, 0)
        for task in self.profile.get("tasks", []):
            if safe_int(task.get("id"), 0) == task_id:
                task["status"] = status
                self.storage.save()
                return task
        raise ValueError(f"Task {task_id} not found.")

    def delete_task(self, task_id):
        task_id = safe_int(task_id, 0)
        original_count = len(self.profile.get("tasks", []))
        self.profile["tasks"] = [
            t
            for t in self.profile.get("tasks", [])
            if safe_int(t.get("id"), 0) != task_id
        ]
        self.storage.save()
        if len(self.profile["tasks"]) == original_count:
            raise ValueError(f"Task {task_id} not found.")

    def mark_done(self, task_id):
        return self.set_task_status(task_id, "done")

    def task_choices(self):
        open_tasks = self.get_tasks(status="open")
        return [
            {
                "id": t.get("id"),
                "label": f"{t.get('title')} ({t.get('subject', 'General')})",
            }
            for t in open_tasks
        ]

    def get_focus_defaults(self, task_id):
        task_id = safe_int(task_id, 0)
        for task in self.profile.get("tasks", []):
            if safe_int(task.get("id"), 0) == task_id:
                return {
                    "subject": task.get("subject", "General"),
                    "task_title": task.get("title", ""),
                    "tags": task.get("tags", []),
                }
        return {"subject": "General", "task_title": "", "tags": []}

    def priority_score(self, task):
        score = 0
        if task.get("due_date"):
            score += 30
        if safe_float(task.get("minutes_logged", 0), 0.0) < 30:
            score += 5
        if task.get("subject") in self.profile.get("goals", {}).get(
            "subject_minutes", {}
        ):
            score += 10
        return score

    def get_sorted_tasks(self):
        tasks = self.get_tasks(status="open")
        return sorted(
            tasks,
            key=lambda t: (
                -self.priority_score(t),
                t.get("due_date") or "9999-12-31",
                t.get("title", ""),
            ),
        )

    def dashboard_summary(self):
        sessions = self.profile.get("sessions", [])
        tasks = self.profile.get("tasks", [])
        exams = self.profile.get("exams", [])
        today_sessions = [s for s in sessions if self._is_today(s.get("ended_at"))]
        today_minutes = sum(
            safe_float(s.get("studied_minutes"), 0.0) for s in today_sessions
        )
        open_tasks = len([t for t in tasks if t.get("status") == "open"])
        total_minutes = sum(safe_float(s.get("studied_minutes"), 0.0) for s in sessions)
        next_exam = None
        if exams:
            for exam in sorted(exams, key=lambda e: e.get("date", "9999-12-31")):
                if exam.get("date") and exam.get("date") >= self._today_str():
                    next_exam = {
                        "name": exam.get("name", "Untitled"),
                        "subject": exam.get("subject", "General"),
                        "countdown": self._countdown_str(exam.get("date")),
                    }
                    break
        recent_sessions = [
            {
                "subject": s.get("subject", "General"),
                "task": s.get("task_title", "Quick session"),
                "minutes": s.get("studied_minutes", 0),
            }
            for s in sessions[-5:]
        ][::-1]
        top_subjects = {}
        for s in sessions:
            subject = s.get("subject", "General")
            minutes = safe_float(s.get("studied_minutes"), 0.0)
            top_subjects[subject] = top_subjects.get(subject, 0) + minutes
        top_subjects_list = sorted(top_subjects.items(), key=lambda x: -x[1])[:5]
        return {
            "today_minutes": today_minutes,
            "today_sessions": len(today_sessions),
            "open_tasks": open_tasks,
            "total_minutes": total_minutes,
            "headline": f"You've studied {int(total_minutes)} minutes across {len(sessions)} sessions.",
            "next_exam": next_exam,
            "recent_sessions": recent_sessions,
            "top_subjects": top_subjects_list,
        }

    def planner_snapshot(self):
        return {
            "plans": self.profile.get("plans", []),
            "exams": self.profile.get("exams", []),
            "topics": self.profile.get("topics", []),
        }

    def save_plan(
        self, plan_id=None, subject="", days="", time="", minutes="", notes=""
    ):
        minutes_int = safe_int(minutes, 45)
        if minutes_int <= 0:
            raise ValueError("Minutes must be positive.")
        if plan_id:
            for plan in self.profile.get("plans", []):
                if safe_int(plan.get("id"), 0) == safe_int(plan_id, 0):
                    plan.update(
                        {
                            "subject": subject or "General",
                            "days": [d.strip() for d in days.split(",") if d.strip()],
                            "time": time or "--:--",
                            "minutes": minutes_int,
                            "notes": notes or "",
                        }
                    )
                    self.storage.save()
                    return plan
        else:
            plan = {
                "id": self.storage.next_id("plan"),
                "subject": subject or "General",
                "days": [d.strip() for d in days.split(",") if d.strip()],
                "time": time or "--:--",
                "minutes": minutes_int,
                "notes": notes or "",
            }
            self.profile.setdefault("plans", []).append(plan)
            self.storage.save()
            return plan
        raise ValueError(f"Plan {plan_id} not found.")

    def delete_plan(self, plan_id):
        plan_id = safe_int(plan_id, 0)
        self.profile["plans"] = [
            p
            for p in self.profile.get("plans", [])
            if safe_int(p.get("id"), 0) != plan_id
        ]
        self.storage.save()

    def save_exam(
        self, exam_id=None, name="", subject="", date="", target_minutes="", notes=""
    ):
        target_min = safe_int(target_minutes, 180)
        if target_min <= 0:
            raise ValueError("Target minutes must be positive.")
        if exam_id:
            for exam in self.profile.get("exams", []):
                if safe_int(exam.get("id"), 0) == safe_int(exam_id, 0):
                    exam.update(
                        {
                            "name": name or "Untitled",
                            "subject": subject or "General",
                            "date": date or "",
                            "target_minutes": target_min,
                            "notes": notes or "",
                            "countdown": self._countdown_str(date),
                        }
                    )
                    self.storage.save()
                    return exam
        else:
            exam = {
                "id": self.storage.next_id("exam"),
                "name": name or "Untitled",
                "subject": subject or "General",
                "date": date or "",
                "target_minutes": target_min,
                "notes": notes or "",
                "countdown": self._countdown_str(date),
            }
            self.profile.setdefault("exams", []).append(exam)
            self.storage.save()
            return exam
        raise ValueError(f"Exam {exam_id} not found.")

    def delete_exam(self, exam_id):
        exam_id = safe_int(exam_id, 0)
        self.profile["exams"] = [
            e
            for e in self.profile.get("exams", [])
            if safe_int(e.get("id"), 0) != exam_id
        ]
        self.storage.save()

    def save_topic(self, topic_id=None, subject="", topic="", progress=0, notes=""):
        progress_int = safe_int(progress, 0)
        if not (0 <= progress_int <= 100):
            raise ValueError("Progress must be between 0 and 100.")
        if topic_id:
            for t in self.profile.get("topics", []):
                if safe_int(t.get("id"), 0) == safe_int(topic_id, 0):
                    t.update(
                        {
                            "subject": subject or "General",
                            "topic": topic or "Untitled",
                            "progress": progress_int,
                            "notes": notes or "",
                        }
                    )
                    self.storage.save()
                    return t
        else:
            t = {
                "id": self.storage.next_id("topic"),
                "subject": subject or "General",
                "topic": topic or "Untitled",
                "progress": progress_int,
                "notes": notes or "",
            }
            self.profile.setdefault("topics", []).append(t)
            self.storage.save()
            return t
        raise ValueError(f"Topic {topic_id} not found.")

    def delete_topic(self, topic_id):
        topic_id = safe_int(topic_id, 0)
        self.profile["topics"] = [
            t
            for t in self.profile.get("topics", [])
            if safe_int(t.get("id"), 0) != topic_id
        ]
        self.storage.save()

    def _is_today(self, timestamp_str):
        if not timestamp_str:
            return False
        try:
            return timestamp_str[:10] == self._today_str()
        except:
            return False

    def _today_str(self):
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d")

    def _countdown_str(self, date_str):
        if not date_str:
            return "TBD"
        try:
            from datetime import datetime

            exam_date = datetime.strptime(date_str[:10], "%Y-%m-%d").date()
            today = datetime.now().date()
            delta = (exam_date - today).days
            if delta < 0:
                return "Past"
            elif delta == 0:
                return "Today"
            elif delta == 1:
                return "Tomorrow"
            else:
                return f"{delta} days"
        except:
            return "TBD"
