from datetime import UTC, datetime

from sqlalchemy import DateTime, TypeDecorator


def utc_now() -> datetime:
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator[datetime]):
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None

        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValueError("UTCDateTime only accepts timezone-aware datetimes")

        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None

        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            return value.replace(tzinfo=UTC)

        return value.astimezone(UTC)
