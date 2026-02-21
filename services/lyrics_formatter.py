import re
import html


def format_lyrics_for_telegraph(lyrics: str) -> str:
    if not lyrics:
        return "<p>Lyrics not found.</p>"

    lyrics = html.escape(lyrics)

    # Normalize newlines
    lyrics = lyrics.replace("\r\n", "\n").replace("\r", "\n")

    # Split by blank lines (verse separation)
    segments = re.split(r"\n\s*\n", lyrics)

    html_parts = []

    for i, segment in enumerate(segments):
        lines = [line.strip() for line in segment.split("\n") if line.strip()]

        for line in lines:
            html_parts.append(f"<p>{line}</p>")

        # Invisible separator paragraph between verses
        if i < len(segments) - 1:
            html_parts.append("<p>&#8203;</p>")

    return "\n".join(html_parts)
