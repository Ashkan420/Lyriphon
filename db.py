"""Database connection pool and channel CRUD operations (asyncpg + Supabase)."""

import asyncpg
import logging
from config import DATABASE_URL

logger = logging.getLogger(__name__)

pool = None


def _require_pool():
    """Return the connection pool, raising if ``init_db()`` was never called."""
    if pool is None:
        raise RuntimeError("Database pool is not initialized. Was init_db() awaited?")
    return pool


async def init_db():
    """Create the global asyncpg connection pool from ``DATABASE_URL``."""
    global pool
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    try:
        pool = await asyncpg.create_pool(
            DATABASE_URL,
            ssl="require",
            min_size=1,
            max_size=5  # keep this low for Supabase free tier
        )
        logger.info("Database pool initialized")
    except Exception:
        logger.exception("Failed to initialize database pool")
        raise

async def get_pool():
    """Return the raw connection pool (for advanced use)."""
    return pool

# --- Channel operations ---

async def get_user_channels(user_id: int):
    """Fetch all channels tracked by *user_id*. Returns ``{channel_id: title}``."""
    p = _require_pool()
    try:
        async with p.acquire() as conn:
            rows = await conn.fetch(
                """
                select channel_id, title
                from channels
                where telegram_user_id = $1
                """,
                user_id
            )
        return {row["channel_id"]: row["title"] for row in rows}
    except RuntimeError:
        raise
    except Exception:
        logger.exception("Failed to fetch channels for user %s", user_id)
        return {}

async def get_users_by_channel(channel_id: int):
    """Return a list of user IDs that are tracking *channel_id*."""
    p = _require_pool()
    try:
        async with p.acquire() as conn:
            rows = await conn.fetch(
                "SELECT telegram_user_id FROM channels WHERE channel_id = $1",
                channel_id
            )
        return [row["telegram_user_id"] for row in rows]
    except RuntimeError:
        raise
    except Exception:
        logger.exception("Failed to fetch users for channel %s", channel_id)
        return []


async def add_channel(user_id: int, chat_id: int, title: str):
    """Insert a channel subscription. Ignores duplicates via ``ON CONFLICT``."""
    p = _require_pool()
    try:
        async with p.acquire() as conn:
            await conn.execute("""
                INSERT INTO channels (telegram_user_id, channel_id, title)
                VALUES ($1, $2, $3)
                ON CONFLICT (telegram_user_id, channel_id) DO NOTHING
            """, user_id, chat_id, title)
    except RuntimeError:
        raise
    except Exception:
        logger.exception(
            "Failed to add channel %s for user %s", chat_id, user_id
        )
        raise

async def remove_channel(user_id: int, chat_id: int):
    """Delete a single channel subscription for *user_id*."""
    p = _require_pool()
    try:
        async with p.acquire() as conn:
            await conn.execute("""
                DELETE FROM channels
                WHERE telegram_user_id=$1 AND channel_id=$2
            """, user_id, chat_id)
    except RuntimeError:
        raise
    except Exception:
        logger.exception(
            "Failed to remove channel %s for user %s", chat_id, user_id
        )
        raise
