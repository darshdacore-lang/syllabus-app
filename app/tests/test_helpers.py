import unittest
import datetime

from app.utils import helpers


class HelpersTestCase(unittest.TestCase):
    def test_parse_date_basic(self):
        d = helpers.parse_date("2026-05-11")
        self.assertIsInstance(d, datetime.date)
        self.assertEqual(d, datetime.date(2026, 5, 11))

    def test_parse_date_empty(self):
        self.assertIsNone(helpers.parse_date(""))
        self.assertIsNone(helpers.parse_date(None))

    def test_parse_date_strict_iso(self):
        self.assertEqual(helpers.parse_date("2026-05-11"), datetime.date(2026, 5, 11))
        self.assertIsNone(helpers.parse_date("05/11/2026"))
        self.assertIsNone(helpers.parse_date("11/05/2026"))

    def test_parse_iso_datetime_zulu(self):
        dt = helpers.parse_iso_datetime("2026-05-11T20:24:29Z")
        self.assertIsInstance(dt, datetime.datetime)
        self.assertIsNone(dt.tzinfo)
        # Ensure the parsed naive datetime represents the same instant as the
        # original Zulu timestamp after accounting for local timezone.
        orig_utc = datetime.datetime(
            2026, 5, 11, 20, 24, 29, tzinfo=datetime.timezone.utc
        )
        orig_ts = orig_utc.timestamp()

        # Interpret returned naive `dt` as local time and compute its epoch.
        local_tz = datetime.datetime.now().astimezone().tzinfo
        dt_local_aware = dt.replace(tzinfo=local_tz)
        parsed_ts = dt_local_aware.timestamp()

        # Allow small rounding differences
        self.assertAlmostEqual(parsed_ts, orig_ts, delta=2)

    def test_parse_tags_and_join(self):
        tags = helpers.parse_tags("a, b, c")
        self.assertEqual(tags, ["a", "b", "c"])
        self.assertEqual(helpers.join_tags(tags), "a, b, c")

    def test_parse_tags_list_input(self):
        tags = helpers.parse_tags(["x", " y "])
        self.assertEqual(tags, ["x", "y"])
        self.assertEqual(helpers.join_tags(tags), "x, y")


if __name__ == "__main__":
    unittest.main()
