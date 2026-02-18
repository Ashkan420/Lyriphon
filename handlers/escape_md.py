# escape special characters for MarkdownV2
def escape_md(text: str):
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    for char in escape_chars:
        text = text.replace(char, f"\\{char}")
    return text