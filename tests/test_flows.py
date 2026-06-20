from core.flows import BaseFlow, AudioFlow, SearchFlow, EditFlow, LyricsFlow, TelegraphFlow


class TestBaseFlow:
    def test_initial_state(self):
        flow = BaseFlow()
        assert flow.lock is False

    def test_reset(self):
        flow = BaseFlow()
        flow.lock = True
        flow.reset()
        assert flow.lock is False

    def test_snapshot(self):
        flow = BaseFlow()
        snap = flow.snapshot()
        assert snap == {"locked": False}

    def test_snapshot_locked(self):
        flow = BaseFlow()
        flow.lock = True
        snap = flow.snapshot()
        assert snap == {"locked": True}


class TestAudioFlow:
    def test_initial_state(self):
        flow = AudioFlow()
        assert flow.file_id is None
        assert flow.title is None
        assert flow.artist is None
        assert flow.message_id is None
        assert flow.caption is None
        assert flow.pending_decision is None
        assert flow.pending_file_id is None
        assert flow.pending_caption is None
        assert flow.pending_telegraph_url is None
        assert flow.send_channel_prompt_id is None
        assert flow.lock is False

    def test_reset_clears_all(self):
        flow = AudioFlow()
        flow.file_id = "abc"
        flow.title = "Test"
        flow.artist = "Artist"
        flow.message_id = 123
        flow.pending_decision = {"key": "val"}
        flow.pending_file_id = "xyz"
        flow.lock = True
        flow.reset()
        assert flow.file_id is None
        assert flow.title is None
        assert flow.pending_decision is None
        assert flow.lock is False

    def test_snapshot(self):
        flow = AudioFlow()
        flow.file_id = "test_id"
        flow.title = "Song"
        snap = flow.snapshot()
        assert snap["file_id"] == "test_id"
        assert snap["title"] == "Song"
        assert snap["has_pending_decision"] is False
        assert snap["locked"] is False


class TestSearchFlow:
    def test_initial_state(self):
        flow = SearchFlow()
        assert flow.results is None
        assert flow.page == 0

    def test_reset(self):
        flow = SearchFlow()
        flow.results = [1, 2, 3]
        flow.page = 5
        flow.lock = True
        flow.reset()
        assert flow.results is None
        assert flow.page == 0
        assert flow.lock is False

    def test_snapshot_no_results(self):
        flow = SearchFlow()
        snap = flow.snapshot()
        assert snap["has_results"] is False
        assert snap["count"] == 0
        assert snap["page"] == 0

    def test_snapshot_with_results(self):
        flow = SearchFlow()
        flow.results = [{"id": 1}, {"id": 2}]
        flow.page = 1
        snap = flow.snapshot()
        assert snap["has_results"] is True
        assert snap["count"] == 2
        assert snap["page"] == 1


class TestEditFlow:
    def test_initial_state(self):
        flow = EditFlow()
        assert flow.field is None
        assert flow.prompt_id is None

    def test_reset(self):
        flow = EditFlow()
        flow.field = "lyrics"
        flow.prompt_id = 999
        flow.reset()
        assert flow.field is None
        assert flow.prompt_id is None

    def test_snapshot(self):
        flow = EditFlow()
        flow.field = "track"
        flow.prompt_id = 42
        snap = flow.snapshot()
        assert snap["field"] == "track"
        assert snap["prompt_id"] == 42


class TestLyricsFlow:
    def test_initial_state(self):
        flow = LyricsFlow()
        assert flow.buffer == []
        assert flow.message_ids == []

    def test_reset(self):
        flow = LyricsFlow()
        flow.buffer = ["line1", "line2"]
        flow.message_ids = [1, 2]
        flow.lock = True
        flow.reset()
        assert flow.buffer == []
        assert flow.message_ids == []
        assert flow.lock is False

    def test_snapshot(self):
        flow = LyricsFlow()
        flow.buffer = ["a", "b", "c"]
        flow.message_ids = [10, 20]
        snap = flow.snapshot()
        assert snap["buffer_lines"] == 3
        assert snap["message_count"] == 2


class TestTelegraphFlow:
    def test_initial_state(self):
        flow = TelegraphFlow()
        assert flow.url is None
        assert flow.path is None
        assert flow.data is None
        assert flow.current_lyrics is None

    def test_reset(self):
        flow = TelegraphFlow()
        flow.url = "https://telegra.ph/test"
        flow.path = "test"
        flow.data = {"track": "Song"}
        flow.current_lyrics = "lyrics"
        flow.reset()
        assert flow.url is None
        assert flow.path is None
        assert flow.data is None
        assert flow.current_lyrics is None

    def test_snapshot(self):
        flow = TelegraphFlow()
        flow.url = "https://telegra.ph/test"
        flow.data = {"track": "Song"}
        snap = flow.snapshot()
        assert snap["has_url"] is True
        assert snap["has_data"] is True
        assert snap["has_lyrics"] is False
