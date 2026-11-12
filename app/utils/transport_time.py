from datetime import datetime, timezone, timedelta

LIMA = timezone(timedelta(hours=-5))


def utc_naive(value: datetime) -> datetime:
    return value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value


def local_time(value: datetime) -> datetime:
    return utc_naive(value).replace(tzinfo=timezone.utc).astimezone(LIMA)
