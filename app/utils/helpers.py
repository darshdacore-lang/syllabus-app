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
    if isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.date):
        return datetime.datetime.combine(value, datetime.time.min)
    if isinstance(value, (int, float)):
        try:
            return datetime.datetime.fromtimestamp(value)
        except (OSError, OverflowError, ValueError):
            return None
    if not isinstance(value, str):
        return None

    value = value.strip()
    if not value:
        return None

    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    try:
        dt = datetime.datetime.fromisoformat(value)
    except ValueError:
        dt = None
        for fmt in (
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
        ):
            try:
                dt = datetime.datetime.strptime(value, fmt)
                break
            except ValueError:
                continue
        if dt is None:
            try:
                return datetime.datetime.fromtimestamp(float(value))
            except (ValueError, OSError, OverflowError):
                return None

    if dt.tzinfo is not None:
        dt = dt.astimezone().replace(tzinfo=None)
    return dt


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
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, (int, float)):
        try:
            return datetime.datetime.fromtimestamp(value).date()
        except (OSError, OverflowError, ValueError):
            return None
    if not isinstance(value, str):
        return None

    value = value.strip()
    if not value:
        return None

    if value.endswith("Z"):
        value = value[:-1]

    for fmt in (
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            return datetime.datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    return None


def join_tags(tags):
    if not tags:
        return ""
    if isinstance(tags, str):
        return tags.strip()
    if isinstance(tags, (list, tuple, set)):
        return ", ".join(str(tag).strip() for tag in tags if str(tag).strip())
    return str(tags).strip()


def parse_tags(value):
    if not value:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(tag).strip() for tag in value if str(tag).strip()]
    return [tag.strip() for tag in str(value).split(",") if tag.strip()]
