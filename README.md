# Lyriphon Bot 🎵

**Lyriphon** is a Telegram bot that allows you to create Telegraph pages with song lyrics, attach them to music files, and send them to channels you manage. It leverages Deezer and LRCLIB APIs for track info and lyrics, providing a seamless experience for music sharing.

---

## Features

- **Search for Songs**: Use `/song <track name>` to find a song on Deezer.
- **Generate Lyrics Page**: Automatically creates a Telegraph page with lyrics.
- **Attach Lyrics Button**: Send a music file, and the bot attaches a “Lyrics” button linking to the Telegraph page.
- **Send to Channels**: Send your music + lyrics to channels you manage.
- **Automatic Escape Handling**: Safely handles special characters in Telegram messages.
- **Supports Multiple Users**: Each user can manage their own music messages and channels independently.

---

## Installation

1. Clone the repository:

```bash
git clone https://github.com/YourUsername/Lyriphon.git
cd Lyriphon
```

2. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

3. Configure your .env file

check .env.example

## Usage

Search for a song:
/song <track name>

Attach a Telegraph button:
Send a music file after generating the Telegraph page to attach the “Lyrics” button.

Send to your channels:
After attaching, choose the channel(s) you manage to share the file + lyrics.

Start command:
/start – Shows instructions and usage info.