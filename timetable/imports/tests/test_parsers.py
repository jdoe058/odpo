from datetime import date, datetime, time
from django.test import SimpleTestCase

from timetable.imports.parsers import as_date, parse_range, parse_time


class AsDateTests(SimpleTestCase):
    def test_datetime(self):
        self.assertEqual(as_date(datetime(2026, 9, 13, 10, 0), 7), date(2026, 9, 13))

    def test_date(self):
        self.assertEqual(as_date(date(2026, 9, 13), 7), date(2026, 9, 13))

    def test_string_dot(self):
        self.assertEqual(as_date("13.09.2026", 7), date(2026, 9, 13))

    def test_string_dash(self):
        self.assertEqual(as_date("2026-09-13", 7), date(2026, 9, 13))

    def test_string_slash(self):
        self.assertEqual(as_date("13/09/2026", 7), date(2026, 9, 13))

    def test_short_year(self):
        self.assertEqual(as_date("13.09.26", 7), date(2026, 9, 13))

    def test_invalid_raises_with_row(self):
        with self.assertRaisesMessage(ValueError, "Строка 7"):
            as_date("не дата", 7)


class ParseTimeTests(SimpleTestCase):
    def test_colon(self):
        self.assertEqual(parse_time("09:30", 7), time(9, 30))

    def test_dot(self):
        self.assertEqual(parse_time("09.30", 7), time(9, 30))

    def test_invalid_raises(self):
        with self.assertRaises(ValueError):
            parse_time("930", 7)


class ParseRangeTests(SimpleTestCase):
    def test_simple(self):
        self.assertEqual(
            parse_range("09:00-10:30", 7),
            (time(9, 0), time(10, 30)),
        )

    def test_missing_dash(self):
        with self.assertRaises(ValueError):
            parse_range("09:00 10:30", 7)

    def test_empty(self):
        with self.assertRaises(ValueError):
            parse_range(None, 7)

