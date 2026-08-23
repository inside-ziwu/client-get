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


def next_beijing_time(hour: int, now_utc: datetime | None = None) -> datetime:
    """返回下一个北京 ``hour:00``（含跨日），aware datetime。

    当前北京时间恰好等于目标时刻时，返回次日同一时刻（不做启动补跑）。
    ``hour`` 越界由 ``time()`` 抛 ``ValueError``。
    """
    now = now_utc or datetime.now(UTC)
    today = beijing_today(now)
    candidate = datetime.combine(today, time(hour=hour), tzinfo=BEIJING_TZ)
    if candidate <= now.astimezone(BEIJING_TZ):
        candidate = candidate + timedelta(days=1)
    return candidate
