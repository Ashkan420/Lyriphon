class BaseFlow:
    """Base class for all session flows."""

    def __init__(self):
        self.lock = False

    def reset(self):
        """Reset this flow to defaults. Subclasses MUST call super().reset()."""
        self.lock = False

    def snapshot(self) -> dict:
        """Return serializable dict for debug inspector."""
        return {"locked": self.lock}


class AudioFlow(BaseFlow):
    """
    Tracks audio file state across the session lifecycle.

    Three conceptual sections:
    1. Search Audio — file attached during search (file_id, title, artist, message_id)
    2. Decision State — pending attach/search decision (pending_decision)
    3. Send-To-Channel — pending channel send after attachment (pending_file_id, etc.)
    """

    def __init__(self):
        super().__init__()
        # --- Search Audio ---
        self.file_id = None
        self.title = None
        self.artist = None
        self.message_id = None
        self.caption = None
        # --- Decision State ---
        self.pending_decision = None
        # --- Send-To-Channel State ---
        self.pending_file_id = None
        self.pending_caption = None
        self.pending_telegraph_url = None
        self.send_channel_prompt_id = None

    def reset(self):
        super().reset()
        self.file_id = None
        self.title = None
        self.artist = None
        self.message_id = None
        self.caption = None
        self.pending_decision = None
        self.pending_file_id = None
        self.pending_caption = None
        self.pending_telegraph_url = None
        self.send_channel_prompt_id = None

    def clear_search_audio(self):
        """Clear the search-audio fields without touching pending/channel state."""
        self.file_id = None
        self.title = None
        self.artist = None
        self.message_id = None

    def snapshot(self) -> dict:
        d = super().snapshot()
        d.update({
            "file_id": self.file_id,
            "title": self.title,
            "artist": self.artist,
            "has_pending_decision": self.pending_decision is not None,
            "has_pending_file_id": self.pending_file_id is not None,
            "send_channel_prompt": self.send_channel_prompt_id is not None,
        })
        return d


class SearchFlow(BaseFlow):
    """Tracks search results and pagination state."""

    def __init__(self):
        super().__init__()
        self.results = None
        self.page = 0

    def reset(self):
        super().reset()
        self.results = None
        self.page = 0

    def snapshot(self) -> dict:
        d = super().snapshot()
        d.update({
            "has_results": self.results is not None,
            "count": len(self.results) if self.results else 0,
            "page": self.page,
        })
        return d


class EditFlow(BaseFlow):
    """Tracks which field is being edited and the prompt message."""

    def __init__(self):
        super().__init__()
        self.field = None
        self.prompt_id = None

    def reset(self):
        super().reset()
        self.field = None
        self.prompt_id = None

    def snapshot(self) -> dict:
        d = super().snapshot()
        d.update({"field": self.field, "prompt_id": self.prompt_id})
        return d


class LyricsFlow(BaseFlow):
    """Tracks multi-message lyrics buffer during edit_lyrics mode."""

    def __init__(self):
        super().__init__()
        self.buffer = []
        self.message_ids = []

    def reset(self):
        super().reset()
        self.buffer = []
        self.message_ids = []

    def snapshot(self) -> dict:
        d = super().snapshot()
        d.update({
            "buffer_lines": len(self.buffer),
            "message_count": len(self.message_ids),
        })
        return d


class TelegraphFlow(BaseFlow):
    """Tracks the current Telegraph page and its metadata."""

    def __init__(self):
        super().__init__()
        self.url = None
        self.path = None
        self.data = None
        self.current_lyrics = None

    def reset(self):
        super().reset()
        self.url = None
        self.path = None
        self.data = None
        self.current_lyrics = None

    def snapshot(self) -> dict:
        d = super().snapshot()
        d.update({
            "has_url": self.url is not None,
            "has_data": self.data is not None,
            "has_lyrics": self.current_lyrics is not None,
        })
        return d
