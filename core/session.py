import json
import functools
import logging
from enum import Enum
from core.flows import BaseFlow, AudioFlow, SearchFlow, EditFlow, LyricsFlow, TelegraphFlow

logger = logging.getLogger(__name__)


class SessionMode(Enum):
    IDLE = "idle"
    SEARCH = "search"
    AUDIO_DECISION = "audio_decision"
    EDIT_FIELD = "edit_field"
    EDIT_LYRICS = "edit_lyrics"


# Soft validation: expected transitions. Logs warning for unexpected paths, doesn't block.
# None means "any origin is valid" (e.g. IDLE can be reached from anywhere).
VALID_TRANSITIONS = {
    SessionMode.IDLE: None,
    SessionMode.SEARCH: {SessionMode.IDLE, SessionMode.AUDIO_DECISION, SessionMode.SEARCH},
    SessionMode.AUDIO_DECISION: {SessionMode.IDLE, SessionMode.SEARCH},
    SessionMode.EDIT_FIELD: {SessionMode.IDLE},
    SessionMode.EDIT_LYRICS: {SessionMode.IDLE},
}


# Documentation only — not enforced automatically.
# When resetting a flow, these dependent flows may also need attention.
# "lyrics depends on edit" means: if edit is reset, lyrics may be in a broken state.
FLOW_RELATIONSHIPS = {
    "edit": [],
    "lyrics": ["edit"],
    "audio": [],
    "search": [],
    "telegraph": [],
}


class Session:
    """Top-level session container. Stored directly in context.user_data["session"]."""

    def __init__(self):
        self.mode = SessionMode.IDLE
        self.version = 0
        self.audio = AudioFlow()
        self.search = SearchFlow()
        self.edit = EditFlow()
        self.lyrics = LyricsFlow()
        self.telegraph = TelegraphFlow()

    def snapshot(self) -> dict:
        """Serializable dict for debug inspector."""
        return {
            "mode": self.mode.value,
            "version": self.version,
            "audio": self.audio.snapshot(),
            "search": self.search.snapshot(),
            "edit": self.edit.snapshot(),
            "lyrics": self.lyrics.snapshot(),
            "telegraph": self.telegraph.snapshot(),
        }


CLEANUP_HOOKS = {}


def get_session(context) -> Session:
    if "session" not in context.user_data:
        context.user_data["session"] = Session()
    return context.user_data["session"]


def reset_session(context):
    """Full reset. ONLY call on /start.

    Note: This replaces the Session object entirely. Stale tasks holding a
    reference to the old Session won't see a version change — they'll see a
    completely different object. This is intentional: a full reset means
    "start over", and stale references should be abandoned.
    """
    context.user_data["session"] = Session()


def reset_flow(flow: BaseFlow):
    """Reset a single flow. Pass the flow object directly."""
    flow.reset()


def capture_version(session: Session) -> int:
    return session.version


def is_stale(session: Session, captured_version: int) -> bool:
    return session.version != captured_version


async def transition(session: Session, to_mode: SessionMode, bot=None, chat_id=None):
    """Transition to to_mode. Captures old mode internally, runs cleanup hooks."""
    old_mode = session.mode
    if old_mode == to_mode:
        return True

    # Soft validation: log warning for unexpected transitions (doesn't block)
    allowed = VALID_TRANSITIONS.get(to_mode)
    if allowed is not None and old_mode not in allowed:
        logger.warning(
            "Unexpected transition: %s -> %s (expected from: %s)",
            old_mode.value, to_mode.value,
            [m.value for m in allowed],
        )

    session.version += 1  # BEFORE hooks so in-flight ops see staleness

    for hook in CLEANUP_HOOKS.get(old_mode, []):
        try:
            await hook(bot, chat_id, session)
        except Exception:
            logger.exception("Cleanup hook failed for mode %s", old_mode.value)

    session.mode = to_mode
    return True


def on_exit_mode(mode: SessionMode, callback):
    CLEANUP_HOOKS.setdefault(mode, []).append(callback)


def set_mode(session: Session, mode: SessionMode):
    """REMOVED: Use 'await transition(session, to_mode, bot, chat_id)' instead."""
    raise RuntimeError(
        "set_mode() removed; use 'await transition(session, to_mode, bot, chat_id)' instead"
    )


def in_mode(session: Session, mode: SessionMode) -> bool:
    return session.mode == mode


def require_mode(mode: SessionMode):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(update, context, *args, **kwargs):
            session = get_session(context)
            if not in_mode(session, mode):
                query = getattr(update, "callback_query", None)
                if query:
                    await query.answer("Session expired or wrong mode.", show_alert=True)
                return
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator


# --- Cleanup hooks: ONLY delete messages, handlers own the reset ---

async def _cleanup_edit(bot, chat_id, session: Session):
    if session.edit.prompt_id and bot and chat_id:
        try:
            await bot.delete_message(chat_id, session.edit.prompt_id)
        except Exception:
            pass
    # Hooks ONLY delete messages — handlers own the reset


async def _cleanup_lyrics(bot, chat_id, session: Session):
    if bot and chat_id:
        for msg_id in session.lyrics.message_ids:
            try:
                await bot.delete_message(chat_id, msg_id)
            except Exception:
                pass
        if session.edit.prompt_id:
            try:
                await bot.delete_message(chat_id, session.edit.prompt_id)
            except Exception:
                pass
    # Hooks ONLY delete messages — handlers own the reset


on_exit_mode(SessionMode.EDIT_FIELD, _cleanup_edit)
on_exit_mode(SessionMode.EDIT_LYRICS, _cleanup_lyrics)


async def session_debug_command(update, context):
    session = get_session(context)
    snap = session.snapshot()
    lines = [f"Mode: {snap['mode']}", f"Version: {snap['version']}"]
    for flow_name in ["audio", "search", "edit", "lyrics", "telegraph"]:
        flow_snap = snap[flow_name]
        lock_str = " [LOCKED]" if flow_snap.pop("locked") else ""
        lines.append(f"\n<b>{flow_name}</b>{lock_str}:")
        for k, v in flow_snap.items():
            lines.append(f"  {k}: {v}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")
