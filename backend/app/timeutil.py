from datetime import datetime, timezone


def iso_utc(value: datetime | None) -> str | None:
    """ISO-8601 with an explicit UTC offset.

    SQLite returns naive datetimes; without an offset the browser would read
    them as local time (UTC+7 in Vietnam -> charts shifted by 7 hours), and
    json.dumps (used by WebSocket.send_json) cannot serialise datetime at all.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()
