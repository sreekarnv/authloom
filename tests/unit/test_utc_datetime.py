from datetime import UTC, datetime, timedelta, timezone

import pytest

from authloom.db.utils.time import UTCDateTime


def test_bind_param_normalizes_aware_datetime_to_naive_utc():
    aware_datetime = datetime(
        2026,
        7,
        29,
        17,
        30,
        45,
        tzinfo=timezone(timedelta(hours=5)),
    )
    utc_type = UTCDateTime()

    stored_datetime = utc_type.process_bind_param(aware_datetime, dialect=None)

    assert stored_datetime == datetime(2026, 7, 29, 12, 30, 45)
    assert stored_datetime.tzinfo is None


def test_bind_param_rejects_naive_datetime():
    naive_datetime = datetime(2026, 7, 29, 12, 30, 45)
    utc_type = UTCDateTime()

    with pytest.raises(ValueError, match="timezone-aware datetimes"):
        utc_type.process_bind_param(naive_datetime, dialect=None)


def test_result_value_returns_timezone_aware_utc_datetime():
    database_datetime = datetime(2026, 7, 29, 12, 30, 45)
    utc_type = UTCDateTime()

    result_datetime = utc_type.process_result_value(database_datetime, dialect=None)

    assert result_datetime == datetime(2026, 7, 29, 12, 30, 45, tzinfo=UTC)
    assert result_datetime.tzinfo is UTC


def test_none_remains_none_for_bind_and_result_values():
    utc_type = UTCDateTime()

    assert utc_type.process_bind_param(None, dialect=None) is None
    assert utc_type.process_result_value(None, dialect=None) is None
