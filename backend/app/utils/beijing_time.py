from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

BEIJING_TZ = ZoneInfo("Asia/Shanghai")


def beijing_today(now_utc: datetime | None = None) -> date:
    now = now_utc or datetime.now(UTC)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now_utc must be timezone-aware")
    return now.astimezone(BEIJING_TZ).date()


def beijing_day_bounds(now_utc: datetime | None = None) -> tuple[datetime, datetime]:
    today = beijing_today(now_utc)
    start = datetime.combine(today, time.min, tzinfo=BEIJING_TZ)
    return start, start + timedelta(days=1)
