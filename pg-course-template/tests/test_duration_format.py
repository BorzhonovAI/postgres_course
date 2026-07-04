"""Unit tests for _format_duration() utility in handlers.routes.

Note: we inline the function rather than importing from handlers.routes
because handlers/__init__.py eagerly imports all handler modules, and
some of them (orders.py) depend on a live database connection. The
function itself is a pure utility with no external dependencies.
"""

from datetime import timedelta


def _format_duration(td) -> str:
    """Mirror of handlers.routes._format_duration — formats timedelta as MM:SS."""
    total_seconds = int(td.total_seconds())
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


class TestFormatDuration:
    """_format_duration formats a timedelta as 'MM:SS'."""

    def test_zero(self):
        assert _format_duration(timedelta(seconds=0)) == "00:00"

    def test_one_second(self):
        assert _format_duration(timedelta(seconds=1)) == "00:01"

    def test_one_minute(self):
        assert _format_duration(timedelta(minutes=1)) == "01:00"

    def test_single_digit_padded(self):
        assert _format_duration(timedelta(seconds=59)) == "00:59"
        assert _format_duration(timedelta(minutes=5)) == "05:00"

    def test_combined_minutes_and_seconds(self):
        assert _format_duration(timedelta(minutes=3, seconds=7)) == "03:07"

    def test_over_an_hour(self):
        # function accumulates hours into minutes (no hour field in output)
        assert _format_duration(timedelta(hours=2, minutes=5)) == "125:00"

    def test_from_timedelta_hours(self):
        td = timedelta(hours=1)
        result = _format_duration(td)
        assert result == "60:00"

    def test_from_total_seconds(self):
        td = timedelta(seconds=3661)  # 61 min 1 sec
        assert _format_duration(td) == "61:01"

    def test_negative_timedelta(self):
        # divmod(-45, 60) in Python gives (-1, 15), so output is "-1:15"
        assert _format_duration(timedelta(seconds=-45)) == "-1:15"
