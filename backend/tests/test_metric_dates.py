import unittest
from datetime import date, datetime, timezone, timedelta

from app.services.metric_dates import absolute_metric_date


class MetricDateTests(unittest.TestCase):
    def test_absolute_strings_are_datetimes_not_strings(self):
        for value in ("2026-10-03", "03/10/2026", "03-10-2026", "October 03, 2026"):
            with self.subTest(value=value):
                self.assertEqual(absolute_metric_date(value), datetime(2026, 10, 3, tzinfo=timezone.utc))

    def test_timezone_is_preserved_by_conversion_to_utc(self):
        self.assertEqual(absolute_metric_date("2026-10-03T09:30:00-03:00"), datetime(2026, 10, 3, 12, 30, tzinfo=timezone.utc))
        self.assertEqual(absolute_metric_date("2026-10-03T12:30:00Z"), datetime(2026, 10, 3, 12, 30, tzinfo=timezone.utc))

    def test_date_and_datetime_objects_are_supported(self):
        expected = datetime(2026, 10, 3, tzinfo=timezone.utc)
        self.assertEqual(absolute_metric_date(date(2026, 10, 3)), expected)
        self.assertEqual(absolute_metric_date(datetime(2026, 10, 3)), expected)
        self.assertEqual(absolute_metric_date(datetime(2026, 10, 3, 3, tzinfo=timezone(timedelta(hours=3)))), expected)

    def test_relative_malformed_or_absent_values_are_unknown_not_invented(self):
        for value in (None, "", "2 hours ago", "hoje", "ontem", "2026-99-99", 0, True, {}, [], "x" * 81):
            with self.subTest(kind=type(value).__name__):
                self.assertIsNone(absolute_metric_date(value))
