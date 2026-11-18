import base64
import unittest

from readme_cards import commit_hours, latest_issue, newest_post_marks, pink_graded, rate_limit_wait, replace_between, streaks


class StreaksTest(unittest.TestCase):
    def test_today_with_nothing_yet_keeps_the_streak(self):
        days = [("2026-11-09", 0), ("2026-11-10", 3), ("2026-11-11", 1), ("2026-11-12", 0)]
        self.assertEqual(streaks(days, "2026-11-12"), (2, 2))

    def test_a_missed_day_ends_the_streak(self):
        days = [("2026-11-08", 5), ("2026-11-09", 5), ("2026-11-10", 5), ("2026-11-11", 0), ("2026-11-12", 2)]
        self.assertEqual(streaks(days, "2026-11-12"), (1, 3))

    def test_future_days_in_the_calendar_are_ignored(self):
        days = [("2026-11-12", 1), ("2026-11-13", 0)]
        self.assertEqual(streaks(days, "2026-11-12"), (1, 1))


class CommitHoursTest(unittest.TestCase):
    def test_uses_the_authors_own_timezone(self):
        hours = commit_hours(["2026-11-12T19:03:20.000-06:00", "2026-11-12T09:00:00+00:00"])
        self.assertEqual((hours[19], hours[9], sum(hours)), (1, 1, 2))


class LatestIssueTest(unittest.TestCase):
    def test_reads_the_first_issue_from_the_newsletter_markdown(self):
        page = (
            "## Past issues\n\n"
            "- [![](https://x.test/card.webp)](https://x.test/issue-2/)Nov 12, 2026 [What to Buy a Homelabber in 2026](https://x.test/issue-2/)\n"
            "- [![](https://x.test/old.webp)](https://x.test/issue-1/)Oct 30, 2026 [Older](https://x.test/issue-1/)\n"
        )
        self.assertEqual(
            latest_issue(page),
            {"image": "https://x.test/card.webp", "url": "https://x.test/issue-2/", "date": "Nov 12, 2026", "title": "What to Buy a Homelabber in 2026"},
        )

    def test_skips_the_reading_time_between_date_and_title(self):
        page = "- [![](https://x.test/card.webp)](https://x.test/issue-3/)Nov 17, 2026 6 min read [Eight panes](https://x.test/issue-3/)\n"
        self.assertEqual(latest_issue(page)["date"], "Nov 17, 2026")
        self.assertEqual(latest_issue(page)["title"], "Eight panes")

    def test_a_changed_layout_fails_loudly(self):
        with self.assertRaises(ValueError):
            latest_issue("no issues here")


class NewestPostMarksTest(unittest.TestCase):
    def test_box_stretches_round_the_picture_and_new_keeps_its_shape(self):
        box, new = newest_post_marks().split("</svg>")[:2]
        self.assertIn('viewBox="0 0 600 300" preserveAspectRatio="none"', box)
        self.assertIn('viewBox="0 0 300 150" preserveAspectRatio="xMidYMid meet"', new)
        self.assertIn('stroke="#ff4fd8"', new)


class ReplaceBetweenTest(unittest.TestCase):
    def test_replaces_only_the_marked_section(self):
        text = "top\n<!-- A -->\nold\n<!-- B -->\nbottom"
        self.assertEqual(replace_between(text, "<!-- A -->", "<!-- B -->", "new"), "top\n<!-- A -->\nnew\n<!-- B -->\nbottom")

    def test_missing_markers_fail_loudly(self):
        with self.assertRaises(ValueError):
            replace_between("no markers", "<!-- A -->", "<!-- B -->", "new")



class RateLimitWaitTest(unittest.TestCase):
    def test_waits_as_long_as_retry_after_says(self):
        self.assertEqual(rate_limit_wait(403, {"retry-after": "30"}, "", 0), 30)

    def test_waits_until_the_primary_limit_resets(self):
        headers = {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1100"}
        self.assertEqual(rate_limit_wait(403, headers, "", 1000), 100)

    def test_secondary_limit_without_retry_after_waits_a_minute(self):
        self.assertEqual(rate_limit_wait(403, {}, '{"message": "You have exceeded a secondary rate limit"}', 0), 60)

    def test_a_403_that_is_not_a_rate_limit_fails(self):
        self.assertIsNone(rate_limit_wait(403, {"x-ratelimit-remaining": "25"}, '{"message": "Resource not accessible"}', 0))

class PinkGradeTest(unittest.TestCase):
    def test_a_grey_photo_comes_out_black_to_pink(self):
        """A dark grey photo (the circus issue's card) ends up the site's pink, not grey."""
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page()
            # Left half near black, right half mid grey: a dark picture, so no invert
            grey = page.evaluate("""() => { const c = document.createElement('canvas'); c.width = 20; c.height = 10;
                const x = c.getContext('2d'); x.fillStyle = '#101010'; x.fillRect(0, 0, 10, 10);
                x.fillStyle = '#707070'; x.fillRect(10, 0, 10, 10); return c.toDataURL('image/png'); }""")
            graded = pink_graded(page, grey, 20)
            pixels = page.evaluate("""async (bytes) => { const img = new Image(); img.src = 'data:image/jpeg;base64,' + bytes; await img.decode();
                const c = document.createElement('canvas'); c.width = 20; c.height = 10; const x = c.getContext('2d'); x.drawImage(img, 0, 0);
                return [Array.from(x.getImageData(2, 5, 1, 1).data.slice(0, 3)), Array.from(x.getImageData(17, 5, 1, 1).data.slice(0, 3))]; }""",
                                   base64.b64encode(graded).decode())
            browser.close()
        dark, light = pixels
        self.assertTrue(all(v < 20 for v in dark), dark)
        for got, want in zip(light, (0xff, 0x4f, 0xd8)):
            self.assertAlmostEqual(got, want, delta=12)


if __name__ == "__main__":
    unittest.main()
