import datetime
import re


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def now_local():
    return datetime.datetime.now()


def now_iso():
    return now_local().isoformat()


def parse_iso_datetime(value):
    if not isinstance(value, str):
        return None
    try:
        return datetime.datetime.fromisoformat(value)
    except ValueError:
        try:
            return datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            return None


def format_minutes(minutes):
    minutes = safe_float(minutes, 0.0)
    if minutes == int(minutes):
        return f"{int(minutes)} min"
    return f"{minutes:.1f} min"


def format_timer(seconds):
    seconds = max(0, safe_int(seconds, 0))
    minutes = seconds // 60
    remainder = seconds % 60
    return f"{minutes:02d}:{remainder:02d}"


def parse_date(value):
    if not value:
        return None
    try:
        return datetime.datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def join_tags(tags):
    if not tags:
        return ""
    if isinstance(tags, str):
        tags = [tags]
    return ", ".join(str(tag).strip() for tag in tags if str(tag).strip())


def parse_tags(value):
    if not value:
        return []
    return [tag.strip() for tag in str(value).split(",") if tag.strip()]
