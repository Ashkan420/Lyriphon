from utils.escape_md import escape_md


class TestEscapeMd:
    def test_no_special_chars(self):
        assert escape_md("hello world") == "hello world"

    def test_underscore(self):
        assert escape_md("hello_world") == "hello\\_world"

    def test_asterisk(self):
        assert escape_md("bold*text") == "bold\\*text"

    def test_square_brackets(self):
        assert escape_md("[link]") == "\\[link\\]"

    def test_parentheses(self):
        assert escape_md("(url)") == "\\(url\\)"

    def test_tilde(self):
        assert escape_md("~strikethrough~") == "\\~strikethrough\\~"

    def test_backtick(self):
        assert escape_md("`code`") == "\\`code\\`"

    def test_hash(self):
        assert escape_md("#heading") == "\\#heading"

    def test_plus(self):
        assert escape_md("a+b") == "a\\+b"

    def test_minus(self):
        assert escape_md("a-b") == "a\\-b"

    def test_equals(self):
        assert escape_md("a=b") == "a\\=b"

    def test_pipe(self):
        assert escape_md("a|b") == "a\\|b"

    def test_curly_braces(self):
        assert escape_md("{json}") == "\\{json\\}"

    def test_dot(self):
        assert escape_md("end.") == "end\\."

    def test_exclamation(self):
        assert escape_md("wow!") == "wow\\!"

    def test_greater_than(self):
        assert escape_md("a>b") == "a\\>b"

    def test_backslash(self):
        assert escape_md("path\\file") == "path\\\\file"

    def test_combined_special_chars(self):
        result = escape_md("Hello! (world) [test]")
        assert "\\!" in result
        assert "\\(" in result
        assert "\\)" in result
        assert "\\[" in result
        assert "\\]" in result

    def test_empty_string(self):
        assert escape_md("") == ""

    def test_real_world_track_name(self):
        result = escape_md("Don't Stop Me Now (Remastered 2011)")
        assert "\\(" in result
        assert "\\)" in result
