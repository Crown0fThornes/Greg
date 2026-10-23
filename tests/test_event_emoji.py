import unittest
from unittest.mock import patch

from custom_types import Item


DAY = 86400
AWARDED = 1700000000


class EventEmojiDisplayTests(unittest.TestCase):
    def award(self, expiration=None, **values):
        with patch("custom_types.time.time", return_value=AWARDED):
            return Item("Event reward", "event_emoji",
                        AWARDED + 244 * DAY if expiration is None else expiration,
                        emoji="🌷", display=values.pop("display", "None"), **values)

    def test_new_award_records_the_award_time(self):
        item = self.award()
        self.assertEqual(item.values["awarded_at"], AWARDED)
        self.assertTrue(item.should_display_event_emoji(AWARDED))

    def test_exact_45_day_boundary(self):
        item = self.award()
        self.assertTrue(item.should_display_event_emoji(AWARDED + 45 * DAY - 1))
        self.assertFalse(item.should_display_event_emoji(AWARDED + 45 * DAY))

    def test_automatic_window_is_independent_of_lifetime(self):
        for expiration in (-1, 0, AWARDED + 90 * DAY, AWARDED + 365 * DAY):
            with self.subTest(expiration=expiration):
                item = self.award(expiration)
                self.assertTrue(item.should_display_event_emoji(AWARDED + 44 * DAY))
                self.assertFalse(item.should_display_event_emoji(AWARDED + 46 * DAY))

    def test_manual_choices_override_automatic_window(self):
        for display in (True, "True"):
            self.assertTrue(self.award(display=display).should_display_event_emoji(AWARDED + 100 * DAY))
        for display in (False, "False"):
            self.assertFalse(self.award(display=display).should_display_event_emoji(AWARDED + DAY))

    def test_expiration_still_applies_to_manual_and_automatic_display(self):
        for display in ("None", "True"):
            item = self.award(AWARDED + 30 * DAY, display=display)
            self.assertTrue(item.should_display_event_emoji(AWARDED + 29 * DAY))
            self.assertFalse(item.should_display_event_emoji(AWARDED + 30 * DAY))

    def test_reload_preserves_timestamp_without_restarting_the_window(self):
        item = self.award()
        with patch("custom_types.time.time", return_value=AWARDED + 100 * DAY):
            loaded = Item.decode(item.encode())
        self.assertEqual(int(loaded.values["awarded_at"]), AWARDED)
        self.assertFalse(loaded.should_display_event_emoji(AWARDED + 100 * DAY))

    def test_old_finite_awards_use_their_original_lifetime(self):
        for name, lifetime in (("Event reward", 21086592), ("Birthday tag", 90 * DAY)):
            with self.subTest(name=name):
                encoded = f"{name};event_emoji;{AWARDED + lifetime};emoji=🌷,display=None"
                with patch("custom_types.time.time", return_value=AWARDED + 100 * DAY):
                    item = Item.decode(encoded)
                self.assertNotIn("awarded_at", item.values)
                self.assertTrue(item.should_display_event_emoji(AWARDED + 44 * DAY))
                self.assertFalse(item.should_display_event_emoji(AWARDED + 45 * DAY))
                self.assertEqual(item.encode(), encoded)

    def test_old_permanent_award_requires_manual_selection(self):
        item = Item.decode("Old gift;event_emoji;-1;emoji=🎁,display=None")
        self.assertFalse(item.should_display_event_emoji(AWARDED))
        item.update_value("display", True)
        self.assertTrue(item.should_display_event_emoji(AWARDED))

    def test_other_item_types_are_unchanged(self):
        item = Item("Shop tag", "tag", -1, emoji="🌷", display="True")
        self.assertNotIn("awarded_at", item.values)
        self.assertFalse(item.should_display_event_emoji(AWARDED))

    def test_future_or_invalid_timestamps_do_not_display_automatically(self):
        self.assertFalse(self.award(awarded_at=AWARDED + DAY).should_display_event_emoji(AWARDED))
        self.assertFalse(self.award(awarded_at="invalid").should_display_event_emoji(AWARDED))


if __name__ == "__main__":
    unittest.main()
