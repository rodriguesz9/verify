"""Absolute dates for database metrics, never provider-relative date strings."""
from datetime import date, datetime, timezone


def absolute_metric_date(value):
    """Return UTC datetime or None; unknown dates must not break persistence.

    A date-only value means midnight UTC for this descriptive metric. Relative
    search snippets (e.g. '2 hours ago') have no stable reference and are not
    converted into invented dates. Original snippets remain in the report.
    """
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(value, datetime.min.time())
    elif isinstance(value, str) and 0 < len(value.strip()) <= 80:
        literal = value.strip()
        try:
            parsed = datetime.fromisoformat(literal.replace("Z", "+00:00"))
        except ValueError:
            parsed = None
            for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%Y %H:%M", "%B %d, %Y"):
                try:
                    parsed = datetime.strptime(literal, fmt)
                    break
                except ValueError:
                    continue
            if parsed is None:
                return None
    else:
        return None
    try:
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        return None
