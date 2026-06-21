from services.lyrics_formatter import format_lyrics_for_telegraph


class TestFormatLyricsForTelegraph:
    def test_empty_string(self):
        result = format_lyrics_for_telegraph("")
        assert result == "<p>Lyrics not found.</p>"

    def test_none(self):
        result = format_lyrics_for_telegraph(None)
        assert result == "<p>Lyrics not found.</p>"

    def test_single_line(self):
        result = format_lyrics_for_telegraph("Hello world")
        assert "<p>Hello world</p>" in result

    def test_multiple_lines_same_verse(self):
        lyrics = "Line one\nLine two\nLine three"
        result = format_lyrics_for_telegraph(lyrics)
        assert "<p>Line one</p>" in result
        assert "<p>Line two</p>" in result
        assert "<p>Line three</p>" in result

    def test_verse_separation(self):
        lyrics = "Verse one line one\nVerse one line two\n\nVerse two line one"
        result = format_lyrics_for_telegraph(lyrics)
        # Should contain zero-width space separator between verses
        assert "&#8203;" in result
        assert "<p>Verse one line one</p>" in result
        assert "<p>Verse two line one</p>" in result

    def test_html_escaping(self):
        lyrics = "Rock & Roll <forever>"
        result = format_lyrics_for_telegraph(lyrics)
        assert "&amp;" in result
        assert "&lt;" in result
        assert "&gt;" in result
        # Original characters should not appear unescaped
        assert "<forever>" not in result

    def test_windows_newlines(self):
        lyrics = "Line one\r\nLine two\r\n\r\nVerse two"
        result = format_lyrics_for_telegraph(lyrics)
        assert "<p>Line one</p>" in result
        assert "<p>Line two</p>" in result
        assert "<p>Verse two</p>" in result

    def test_old_mac_newlines(self):
        lyrics = "Line one\rLine two"
        result = format_lyrics_for_telegraph(lyrics)
        assert "<p>Line one</p>" in result
        assert "<p>Line two</p>" in result

    def test_strips_whitespace_lines(self):
        lyrics = "  Line one  \n  Line two  "
        result = format_lyrics_for_telegraph(lyrics)
        assert "<p>Line one</p>" in result
        assert "<p>Line two</p>" in result

    def test_empty_lines_between_verses_counted_correctly(self):
        lyrics = "V1L1\nV1L2\n\n\nV2L1"
        result = format_lyrics_for_telegraph(lyrics)
        # Multiple blank lines still produce separators
        assert "<p>V1L1</p>" in result
        assert "<p>V2L1</p>" in result

    def test_no_separator_at_end(self):
        lyrics = "Only verse"
        result = format_lyrics_for_telegraph(lyrics)
        assert "&#8203;" not in result
