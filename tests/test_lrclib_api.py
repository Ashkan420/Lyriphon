import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import httpx


def _make_response(json_data, status_code=200):
    """Create a mock httpx Response with synchronous .json() and .raise_for_status()."""
    resp = MagicMock()
    resp.json.return_value = json_data
    resp.status_code = status_code
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"{status_code}", request=MagicMock(), response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


class TestGetLyrics:
    @pytest.fixture(autouse=True)
    def _patch_client(self):
        self.mock_client = AsyncMock()
        with patch("services.lrclib_api._client", self.mock_client):
            yield

    @pytest.mark.asyncio
    async def test_returns_plain_lyrics(self):
        from services.lrclib_api import get_lyrics
        self.mock_client.get.return_value = _make_response([
            {"plainLyrics": "Hello world\nSecond line", "syncedLyrics": None}
        ])

        result = await get_lyrics("Song", "Artist")
        assert result == "Hello world\nSecond line"

    @pytest.mark.asyncio
    async def test_returns_synced_lyrics_when_no_plain(self):
        from services.lrclib_api import get_lyrics
        self.mock_client.get.return_value = _make_response([
            {"plainLyrics": None, "syncedLyrics": "[00:01]Synced line"}
        ])

        result = await get_lyrics("Song", "Artist")
        assert result == "[00:01]Synced line"

    @pytest.mark.asyncio
    async def test_returns_none_when_empty_results(self):
        from services.lrclib_api import get_lyrics
        self.mock_client.get.return_value = _make_response([])

        result = await get_lyrics("Song", "Artist", retries=0)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_lyrics_in_result(self):
        from services.lrclib_api import get_lyrics
        self.mock_client.get.return_value = _make_response([
            {"plainLyrics": None, "syncedLyrics": None}
        ])

        result = await get_lyrics("Song", "Artist", retries=0)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_exception(self):
        from services.lrclib_api import get_lyrics
        self.mock_client.get.side_effect = httpx.HTTPError("timeout")

        result = await get_lyrics("Song", "Artist", retries=0)
        assert result is None

    @pytest.mark.asyncio
    async def test_retries_on_empty_results(self):
        from services.lrclib_api import get_lyrics

        empty_resp = _make_response([])
        success_resp = _make_response([
            {"plainLyrics": "Found on retry", "syncedLyrics": None}
        ])

        self.mock_client.get.side_effect = [empty_resp, success_resp]

        with patch("services.lrclib_api.asyncio.sleep", new_callable=AsyncMock):
            result = await get_lyrics("Song", "Artist", retries=1, delay=0.01)

        assert result == "Found on retry"
        assert self.mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_retries_on_exception(self):
        from services.lrclib_api import get_lyrics

        success_resp = _make_response([
            {"plainLyrics": "Success after error", "syncedLyrics": None}
        ])

        self.mock_client.get.side_effect = [
            httpx.HTTPError("timeout"),
            success_resp,
        ]

        with patch("services.lrclib_api.asyncio.sleep", new_callable=AsyncMock):
            result = await get_lyrics("Song", "Artist", retries=1, delay=0.01)

        assert result == "Success after error"

    @pytest.mark.asyncio
    async def test_exhausts_retries_returns_none(self):
        from services.lrclib_api import get_lyrics
        self.mock_client.get.side_effect = httpx.HTTPError("timeout")

        with patch("services.lrclib_api.asyncio.sleep", new_callable=AsyncMock):
            result = await get_lyrics("Song", "Artist", retries=2, delay=0.01)

        assert result is None
        assert self.mock_client.get.call_count == 3  # initial + 2 retries
