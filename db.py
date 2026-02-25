#db.py
import asyncpg
from config import DATABASE_URL

pool = None

async def init_db():
    global pool
    pool = await asyncpg.create_pool(
        DATABASE_URL,
        ssl="require",
        min_size=1,
        max_size=5  # keep this low for Supabase free tier
    )

async def get_pool():
    return pool

async def get_user_channels(user_id: int):
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            select channel_id, title
            from channels
            where telegram_user_id = $1
            """,
            user_id
        )

    return {row["channel_id"]: row["title"] for row in rows}

async def get_users_by_channel(channel_id: int):
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT telegram_user_id FROM channels WHERE channel_id = $1",
            channel_id
        )
    return [row["telegram_user_id"] for row in rows]


async def add_channel(user_id: int, chat_id: int, title: str):
    # only insert if it doesn't exist
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO channels (telegram_user_id, channel_id, title)
            VALUES ($1, $2, $3)
            ON CONFLICT (telegram_user_id, channel_id) DO NOTHING
        """, user_id, chat_id, title)

async def remove_channel(user_id: int, chat_id: int):
    async with pool.acquire() as conn:
        await conn.execute("""
            DELETE FROM channels
            WHERE telegram_user_id=$1 AND channel_id=$2
        """, user_id, chat_id)



