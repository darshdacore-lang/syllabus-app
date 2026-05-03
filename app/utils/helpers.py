from datetime import date, datetime


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
    return datetime.now().astimezone()


def now_iso():
    return now_local().isoformat()


def parse_iso_datetime(value):
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=now_local().tzinfo)
    return parsed


def parse_date(value):
    if not value:
        return None

    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def parse_tags(value):
    if isinstance(value, str):
        return [tag.strip() for tag in value.split(",") if tag.strip()]
    if isinstance(value, list):
        return [str(tag).strip() for tag in value if str(tag).strip()]
    return []


def join_tags(tags):
    return ", ".join(parse_tags(tags))


def format_timer(total_seconds):
    seconds = max(0, safe_int(total_seconds, 0))
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def format_minutes(total_minutes):
    minutes = safe_float(total_minutes, 0.0)
    if minutes.is_integer():
        return f"{int(minutes)} min"
    return f"{minutes:.1f} min"


def today_local_date():
    return now_local().date()


def days_until(value):
    parsed = parse_date(value)
    if parsed is None:
        return None
    return (parsed - today_local_date()).days


def humanize_due_date(value):
    parsed = parse_date(value)
    if parsed is None:
        return "No date"

    delta = (parsed - today_local_date()).days
    if delta == 0:
        return "Today"
    if delta == 1:
        return "Tomorrow"
    if delta > 1:
        return f"In {delta} days"
    if delta == -1:
        return "1 day overdue"
    return f"{abs(delta)} days overdue"
