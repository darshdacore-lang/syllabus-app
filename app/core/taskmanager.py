from datetime import date
from collections import Counter

from app.utils.helpers import (
    days_until,
    format_minutes,
    humanize_due_date,
    now_iso,
    parse_date,
    parse_iso_datetime,
    parse_tags,
    safe_float,
    safe_int,
    today_local_date,
)


class TaskManager:
    def __init__(self, storage):
        self.storage = storage
        self.profile = storage.profile
        self._normalize_profile()

    def _normalize_profile(self):
        changed = False

        if "goals" not in self.profile or not isinstance(self.profile["goals"], dict):
            self.profile["goals"] = {}
            changed = True

        self.profile["goals"].setdefault("daily_minutes", 120)
        self.profile["goals"].setdefault("weekly_sessions", 10)
        self.profile["goals"].setdefault("subject_minutes", {})

        normalized_tasks = []
        for task in self.storage.get_collection("tasks"):
            normalized = {
                "id": safe_int(task.get("id"), 0),
                "title": (task.get("title") or "").strip(),
                "subject": (task.get("subject") or "General").strip() or "General",
                "details": (task.get("details") or "").strip(),
                "due_date": (task.get("due_date") or "").strip(),
                "tags": parse_tags(task.get("tags")),
                "status": (task.get("status") or "open").strip() or "open",
                "minutes_logged": round(safe_float(task.get("minutes_logged"), 0.0), 2),
                "created_at": task.get("created_at") or now_iso(),
            }
            if normalized["title"]:
                if normalized["id"] <= 0:
                    normalized["id"] = self.storage.next_id("task")
                    changed = True
                normalized_tasks.append(normalized)

        if normalized_tasks != self.storage.get_collection("tasks"):
            self.profile["tasks"] = normalized_tasks
            changed = True

        if changed:
            self.storage.save()

    def list_tasks(self, include_done=True):
        tasks = list(self.storage.get_collection("tasks"))
        if not include_done:
            tasks = [task for task in tasks if task.get("status") != "done"]

        return sorted(
            tasks,
            key=lambda task: (
                task.get("status") == "done",
                parse_date(task.get("due_date")) or date.max,
                task.get("title", "").lower(),
            ),
        )

    def get_task(self, task_id):
        task_id = safe_int(task_id, 0)
        for task in self.storage.get_collection("tasks"):
            if safe_int(task.get("id"), 0) == task_id:
                return task
        return None

    def task_choices(self):
        choices = []
        for task in self.list_tasks(include_done=False):
            due_label = humanize_due_date(task.get("due_date"))
            label = f"{task['title']} - {task['subject']} - {due_label}"
            choices.append({"id": task["id"], "label": label, "task": task})
        return choices

    def get_focus_defaults(self, task_id):
        task = self.get_task(task_id)
        if not task:
            return {"subject": "General", "task_title": "", "tags": []}
        return {
            "subject": task.get("subject") or "General",
            "task_title": task.get("title") or "",
            "tags": list(task.get("tags", [])),
        }

    def add_task(self, title, subject, details="", due_date="", tags=None):
        title = (title or "").strip()
        if not title:
            raise ValueError("Task title is required.")

        task = {
            "id": self.storage.next_id("task"),
            "title": title,
            "subject": (subject or "General").strip() or "General",
            "details": (details or "").strip(),
            "due_date": (due_date or "").strip(),
            "tags": parse_tags(tags),
            "status": "open",
            "minutes_logged": 0,
            "created_at": now_iso(),
        }
        self.storage.get_collection("tasks").append(task)
        self.storage.save()
        return task

    def set_task_status(self, task_id, status):
        task = self.get_task(task_id)
        if not task:
            raise ValueError("Task not found.")
        task["status"] = status
        self.storage.save()
        return task

    def planner_snapshot(self):
        plans = []
        for plan in self.storage.get_collection("plans"):
            plans.append(
                {
                    "subject": (plan.get("subject") or "General").strip() or "General",
                    "schedule": ", ".join(plan.get("days", [])) or "Flexible",
                    "time": plan.get("time") or "--:--",
                    "minutes": safe_int(plan.get("minutes"), 0),
                    "notes": plan.get("notes") or "",
                }
            )

        exams = []
        for exam in self.storage.get_collection("exams"):
            exams.append(
                {
                    "name": (exam.get("name") or "Untitled Exam").strip(),
                    "subject": (exam.get("subject") or "General").strip() or "General",
                    "date": exam.get("date") or "",
                    "countdown": humanize_due_date(exam.get("date")),
                    "days_until": days_until(exam.get("date")),
                    "target_minutes": safe_int(exam.get("target_minutes"), 0),
                }
            )
        exams.sort(key=lambda exam: exam["days_until"] if exam["days_until"] is not None else 10**6)

        topics = []
        for topic in self.storage.get_collection("topics"):
            topics.append(
                {
                    "subject": (topic.get("subject") or "General").strip() or "General",
                    "topic": (topic.get("topic") or "Untitled Topic").strip(),
                    "progress": max(0, min(100, safe_int(topic.get("progress"), 0))),
                    "notes": topic.get("notes") or "",
                }
            )

        return {"plans": plans, "exams": exams, "topics": topics}

    def dashboard_summary(self):
        sessions = list(self.storage.get_collection("sessions"))
        tasks = self.list_tasks(include_done=True)
        today = today_local_date()
        goals = self.profile.get("goals", {})

        today_minutes = 0.0
        today_sessions = 0
        subject_totals = Counter()
        recent_sessions = []

        for session in sessions:
            ended_at = parse_iso_datetime(session.get("ended_at"))
            studied_minutes = safe_float(session.get("studied_minutes"), 0.0)
            subject = (session.get("subject") or "General").strip() or "General"
            if studied_minutes > 0:
                subject_totals[subject] += studied_minutes

            if ended_at:
                recent_sessions.append(
                    {
                        "subject": subject,
                        "task": session.get("task_title") or session.get("task") or "-",
                        "minutes": studied_minutes,
                        "ended_at": ended_at,
                    }
                )
                if ended_at.date() == today:
                    today_minutes += studied_minutes
                    today_sessions += 1

        recent_sessions.sort(key=lambda session: session["ended_at"], reverse=True)

        next_exam = None
        for exam in self.planner_snapshot()["exams"]:
            if exam["days_until"] is None or exam["days_until"] < 0:
                continue
            next_exam = exam
            break

        open_tasks = len([task for task in tasks if task.get("status") != "done"])
        done_tasks = len(tasks) - open_tasks
        daily_goal = safe_int(goals.get("daily_minutes"), 120)
        weekly_goal = safe_int(goals.get("weekly_sessions"), 10)

        return {
            "today_minutes": round(today_minutes, 1),
            "today_sessions": today_sessions,
            "total_minutes": round(sum(subject_totals.values()), 1),
            "open_tasks": open_tasks,
            "done_tasks": done_tasks,
            "daily_goal": daily_goal,
            "weekly_goal": weekly_goal,
            "recent_sessions": recent_sessions[:6],
            "top_subjects": subject_totals.most_common(5),
            "next_exam": next_exam,
            "headline": (
                f"{format_minutes(today_minutes)} studied today across {today_sessions} sessions"
            ),
        }
