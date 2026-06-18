import json
import functools


class SessionMode:
    IDLE = "idle"
    SEARCH = "search"
    AUDIO_DECISION = "audio_decision"
    EDIT_FIELD = "edit_field"
    EDIT_LYRICS = "edit_lyrics"


CLEANUP_HOOKS = {}


def _default_session():
    return {
        "mode": SessionMode.IDLE,
        "telegraph": {
            "url": None,
            "path": None,
            "data": None,
            "current_lyrics": None,
        },
        "audio": {
            "file_id": None,
            "title": None,
            "artist": None,
            "message_id": None,
            "caption": None,
            "pending_decision": None,
            "pending_file_id": None,
            "pending_caption": None,
            "pending_telegraph_url": None,
            "send_channel_prompt_id": None,
        },
        "search": {
            "results": None,
            "page": 0,
        },
        "lyrics": {
            "buffer": [],
            "message_ids": [],
            "finalizing": False,
        },
        "edit": {
            "field": None,
            "prompt_id": None,
        },
    }


def get_session(context):
    if "session" not in context.user_data:
        context.user_data["session"] = _default_session()
    return context.user_data["session"]


def reset_session(context):
    context.user_data["session"] = _default_session()


def set_mode(session, mode):
    session["mode"] = mode


def in_mode(session, mode):
    return session["mode"] == mode


def on_exit_mode(mode, callback):
    CLEANUP_HOOKS.setdefault(mode, []).append(callback)


async def transition(session, from_mode, to_mode, bot=None, chat_id=None):
    if session["mode"] != from_mode:
        return False

    for hook in CLEANUP_HOOKS.get(from_mode, []):
        await hook(bot, chat_id, session)

    session["mode"] = to_mode
    return True


def _reset_edit_sub(session):
    session["edit"]["field"] = None
    session["edit"]["prompt_id"] = None


def _reset_lyrics_sub(session):
    session["lyrics"]["buffer"] = []
    session["lyrics"]["message_ids"] = []
    session["lyrics"]["finalizing"] = False


async def _cleanup_edit(bot, chat_id, session):
    if not bot or not chat_id:
        _reset_edit_sub(session)
        return

    prompt_id = session["edit"].get("prompt_id")
    if prompt_id:
        try:
            await bot.delete_message(chat_id, prompt_id)
        except Exception:
            pass

    _reset_edit_sub(session)


async def _cleanup_lyrics(bot, chat_id, session):
    if not bot or not chat_id:
        _reset_lyrics_sub(session)
        return

    for msg_id in session["lyrics"].get("message_ids", []):
        try:
            await bot.delete_message(chat_id, msg_id)
        except Exception:
            pass

    prompt_id = session["edit"].get("prompt_id")
    if prompt_id:
        try:
            await bot.delete_message(chat_id, prompt_id)
        except Exception:
            pass

    _reset_edit_sub(session)
    _reset_lyrics_sub(session)


on_exit_mode(SessionMode.EDIT_FIELD, _cleanup_edit)
on_exit_mode(SessionMode.EDIT_LYRICS, _cleanup_lyrics)


def require_mode(mode):
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


async def session_debug_command(update, context):
    session = get_session(context)
    text = f"<pre>{json.dumps(session, indent=2, default=str)}</pre>"
    await update.message.reply_text(text, parse_mode="HTML")
