# Lyriphon Bot 🎵

**Lyriphon** is a Telegram bot for building Telegraph lyric pages and attaching them to music files. Search a track, the bot pulls metadata from Deezer and lyrics from LRCLIB, publishes a formatted Telegraph page, and lets you attach a "Lyrics" button to an audio file before forwarding it to channels you manage.

---

## Features

- **Song search** — `/song <track name>` searches Deezer and returns a paginated list of matches.
- **Automatic lyrics pages** — generates a [Telegraph](https://telegra.ph) page with cover art, metadata, and lyrics fetched from LRCLIB.
- **Attach to audio** — send a music file and the bot attaches an inline **Lyrics** button linking to the Telegraph page.
- **Send to channels** — forward the tagged file to any channel where the bot is an admin; the bot tracks your channels automatically.
- **Inline mode** — type `@your_bot_name <query>` in any chat to search and share without opening a DM.
- **Metadata & lyrics editing** — edit individual fields (title, artist, album, links, cover) or rewrite lyrics across multiple messages, then re-publish the page.
- **Per-user sessions** — each user has an independent finite-state session, with versioning to guard against stale async updates.

---

## How it works

```
/song ─► Deezer search ─► pick track ─► LRCLIB lyrics ─► Telegraph page
                                                              │
            send audio file ─► attach "Lyrics" button ◄───────┘
                                       │
                              send to your channel(s)
```

External services:
- **Deezer API** — track / album / artist metadata (`services/deezer_api.py`)
- **LRCLIB API** — plain & synced lyrics, with retry/backoff (`services/lrclib_api.py`)
- **Telegraph API** — page creation & editing (`services/telegraph_service.py`)
- **PostgreSQL** (e.g. Supabase) — stores which channels each user manages

---

## Project structure

```
main.py                     Entry point; registers all handlers and starts polling
config.py                   Loads & validates environment variables
db.py                       asyncpg pool + channel persistence
core/
  session.py                SessionMode FSM, transitions, stale-version checks
  flows.py                  Per-feature session state (audio, search, edit, lyrics, telegraph)
handlers/
  start.py                  /start and /help
  song_search.py            /song search + result pagination
  callbacks.py              Track selection, editing, audio decisions, send-to-channel
  music_file.py             Handles uploaded audio files
  channel_tracker.py        Tracks channels where the bot is added/removed as admin
  inline_search.py          Inline-mode search
services/
  deezer_api.py             Deezer metadata
  lrclib_api.py             Lyrics retrieval
  telegraph_service.py      Telegraph page build/publish
  lyrics_formatter.py       Lyrics → Telegraph HTML
utils/
  telegram.py               Shared Telegram helpers (safe delete, attach flow, etc.)
  retry.py                  Sync/async retry with exponential backoff
  url_validation.py         URL validation + SSRF guard
  escape_md.py              MarkdownV2 escaping
scripts/
  generate_telegraph_token.py   One-off Telegraph access-token generator
tests/                      pytest suite
```

---

## Requirements

- Python **3.11+**
- A PostgreSQL database (the project is set up for [Supabase](https://supabase.com), but any Postgres works)
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- A Telegraph access token

---

## Setup

1. **Clone and create a virtual environment**

   ```bash
   git clone https://github.com/Ashkan420/Lyriphon.git
   cd Lyriphon
   python -m venv .venv
   source .venv/bin/activate      # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Create the database table**

   ```sql
   CREATE TABLE channels (
       telegram_user_id BIGINT NOT NULL,
       channel_id       BIGINT NOT NULL,
       title            TEXT,
       PRIMARY KEY (telegram_user_id, channel_id)
   );
   ```

3. **Generate a Telegraph access token**

   ```bash
   python scripts/generate_telegraph_token.py
   ```

   Copy the printed token into your `.env`.

4. **Configure environment variables**

   Copy `.env.example` to `.env` and fill it in:

   | Variable | Required | Description |
   | --- | --- | --- |
   | `BOT_TOKEN` | ✅ | Bot token from @BotFather |
   | `TELEGRAPH_ACCESS_TOKEN` | ✅ | Token from the script above |
   | `DATABASE_URL` | ✅ | PostgreSQL connection string |
   | `BOT_OWNER_ID` | optional | Your Telegram user ID; restricts the `/session` debug command |

   The bot refuses to start if any required variable is missing.

5. **Run the bot**

   ```bash
   python main.py
   ```

   It runs in long-polling mode. A `Procfile` (`worker: python main.py`) is included for Heroku-style deployments.

---

## Usage

| Command | Description |
| --- | --- |
| `/start` | Reset your session and show the welcome message |
| `/help` | Show usage instructions |
| `/song <track name>` | Search Deezer and start a lyrics page |
| `/done` | Finish multi-message lyrics editing |
| `/cancel` | Cancel the current edit |
| `/session` | (owner only) Dump the current session state for debugging |

**Typical flow**

1. `/song bohemian rhapsody`
2. Pick a track from the results.
3. The bot creates a Telegraph page with the lyrics.
4. Send (or forward) the music file in the chat — the bot attaches a **Lyrics** button.
5. Choose a channel to publish the tagged file. The bot must be an admin in that channel; it learns about your channels automatically when you add it.

**Inline mode**: type `@your_bot_name <query>` in any chat to search directly.

---

## Testing

```bash
pip install -r requirements.txt        # includes pytest + pytest-asyncio
python -m pytest -q
```

---

## Configuration notes

- `CHANNEL_LINK` and `DEEZLOAD_BOT` are defined in `config.py`. Update them if you fork the project for your own channel/bot.
- The database pool is capped at 5 connections (`db.py`) to stay within Supabase free-tier limits.
