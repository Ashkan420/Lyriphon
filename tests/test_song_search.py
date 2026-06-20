from handlers.song_search import format_duration, build_track_buttons, PAGE_SIZE


class TestFormatDuration:
    def test_zero_seconds(self):
        assert format_duration(0) == "0:00"

    def test_exact_minute(self):
        assert format_duration(60) == "1:00"

    def test_one_second(self):
        assert format_duration(1) == "0:01"

    def test_typical_song(self):
        assert format_duration(215) == "3:35"

    def test_long_song(self):
        assert format_duration(600) == "10:00"

    def test_under_ten_seconds(self):
        assert format_duration(9) == "0:09"

    def test_59_seconds(self):
        assert format_duration(59) == "0:59"


class TestBuildTrackButtons:
    def _make_results(self, count):
        return [
            {
                "id": i,
                "title": f"Track {i}",
                "artist": {"name": f"Artist {i}"},
                "duration": 200 + i,
            }
            for i in range(count)
        ]

    def test_single_result(self):
        results = self._make_results(1)
        buttons = build_track_buttons(results, page=0)
        # One track button, no nav
        assert len(buttons) == 1
        assert buttons[0][0].text.startswith("Track 0")
        assert buttons[0][0].callback_data == "track_0"

    def test_full_page(self):
        results = self._make_results(PAGE_SIZE)
        buttons = build_track_buttons(results, page=0)
        assert len(buttons) == PAGE_SIZE  # no nav needed

    def test_next_button_present(self):
        results = self._make_results(PAGE_SIZE + 1)
        buttons = build_track_buttons(results, page=0)
        # Last row should have nav button(s)
        nav_row = buttons[-1]
        nav_texts = [b.text for b in nav_row]
        assert any("Next" in t for t in nav_texts)

    def test_previous_button_present_on_page_1(self):
        results = self._make_results(PAGE_SIZE * 2)
        buttons = build_track_buttons(results, page=1)
        nav_row = buttons[-1]
        nav_texts = [b.text for b in nav_row]
        assert any("Previous" in t for t in nav_texts)

    def test_first_button_on_last_page(self):
        results = self._make_results(PAGE_SIZE * 3)
        last_page = 2
        buttons = build_track_buttons(results, page=last_page)
        nav_row = buttons[-1]
        nav_texts = [b.text for b in nav_row]
        assert any("First" in t for t in nav_texts)

    def test_no_nav_buttons_single_page(self):
        results = self._make_results(3)
        buttons = build_track_buttons(results, page=0)
        # All buttons should be track buttons
        for row in buttons:
            for btn in row:
                assert btn.callback_data.startswith("track_")

    def test_correct_page_slice(self):
        results = self._make_results(PAGE_SIZE * 2)
        buttons = build_track_buttons(results, page=1)
        # First track on page 1 should be Track 5 (index 5)
        first_track_btn = buttons[0][0]
        assert f"Track {PAGE_SIZE}" in first_track_btn.text
