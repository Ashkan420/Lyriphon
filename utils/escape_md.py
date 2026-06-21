"""Escape special characters for Telegram's MarkdownV2 parse mode."""


def escape_md(text: str):
    """Escape all MarkdownV2 special characters in *text*."""
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    for char in escape_chars:
        text = text.replace(char, f"\\{char}")
    return text
