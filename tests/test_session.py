import pytest
from unittest.mock import AsyncMock, MagicMock
from core.session import (
    Session, SessionMode, get_session, reset_session, reset_flow,
    capture_version, is_stale, transition, in_mode, set_mode,
    VALID_TRANSITIONS
)


class TestSession:
    def test_initial_state(self):
        session = Session()
        assert session.mode == SessionMode.IDLE
        assert session.version == 0

    def test_snapshot(self):
        session = Session()
        snap = session.snapshot()
        assert snap["mode"] == "idle"
        assert snap["version"] == 0
        assert "audio" in snap
        assert "search" in snap
        assert "edit" in snap
        assert "lyrics" in snap
        assert "telegraph" in snap


class TestGetSession:
    def test_creates_new_session(self):
        context = MagicMock()
        context.user_data = {}
        session = get_session(context)
        assert isinstance(session, Session)
        assert context.user_data["session"] is session

    def test_returns_existing_session(self):
        context = MagicMock()
        existing = Session()
        context.user_data = {"session": existing}
        session = get_session(context)
        assert session is existing


class TestResetSession:
    def test_replaces_session(self):
        context = MagicMock()
        old_session = Session()
        old_session.version = 5
        context.user_data = {"session": old_session}
        reset_session(context)
        new_session = context.user_data["session"]
        assert new_session is not old_session
        assert new_session.version == 0


class TestResetFlow:
    def test_resets_flow_object(self):
        session = Session()
        session.edit.field = "track"
        session.edit.prompt_id = 42
        reset_flow(session.edit)
        assert session.edit.field is None
        assert session.edit.prompt_id is None


class TestVersioning:
    def test_capture_version(self):
        session = Session()
        session.version = 7
        assert capture_version(session) == 7

    def test_is_stale_false(self):
        session = Session()
        v = capture_version(session)
        assert is_stale(session, v) is False

    def test_is_stale_true(self):
        session = Session()
        v = capture_version(session)
        session.version += 1
        assert is_stale(session, v) is True


class TestInMode:
    def test_matches(self):
        session = Session()
        session.mode = SessionMode.SEARCH
        assert in_mode(session, SessionMode.SEARCH) is True

    def test_no_match(self):
        session = Session()
        assert in_mode(session, SessionMode.SEARCH) is False


class TestSetModeRemoved:
    def test_raises_runtime_error(self):
        session = Session()
        with pytest.raises(RuntimeError, match="set_mode\\(\\) removed"):
            set_mode(session, SessionMode.IDLE)


@pytest.mark.asyncio
class TestTransition:
    async def test_transition_changes_mode(self):
        session = Session()
        await transition(session, SessionMode.SEARCH)
        assert session.mode == SessionMode.SEARCH

    async def test_transition_increments_version(self):
        session = Session()
        v_before = session.version
        await transition(session, SessionMode.SEARCH)
        assert session.version == v_before + 1

    async def test_transition_same_mode_noop(self):
        session = Session()
        v_before = session.version
        await transition(session, SessionMode.IDLE)
        assert session.version == v_before

    async def test_transition_to_idle_from_anywhere(self):
        session = Session()
        session.mode = SessionMode.SEARCH
        result = await transition(session, SessionMode.IDLE)
        assert result is True
        assert session.mode == SessionMode.IDLE

    async def test_transition_runs_cleanup_hooks(self):
        from core.session import CLEANUP_HOOKS
        session = Session()
        session.mode = SessionMode.EDIT_FIELD
        session.edit.prompt_id = 123

        bot = AsyncMock()
        chat_id = 456

        await transition(session, SessionMode.IDLE, bot, chat_id)
        # The cleanup hook for EDIT_FIELD should try to delete the prompt
        bot.delete_message.assert_called_with(chat_id, 123)


class TestValidTransitions:
    def test_idle_accepts_any(self):
        assert VALID_TRANSITIONS[SessionMode.IDLE] is None

    def test_search_valid_origins(self):
        assert SessionMode.IDLE in VALID_TRANSITIONS[SessionMode.SEARCH]
        assert SessionMode.AUDIO_DECISION in VALID_TRANSITIONS[SessionMode.SEARCH]

    def test_edit_field_from_idle(self):
        assert SessionMode.IDLE in VALID_TRANSITIONS[SessionMode.EDIT_FIELD]
