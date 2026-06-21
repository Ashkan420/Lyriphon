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


class TestSearchTracks:
    @pytest.fixture(autouse=True)
    def _patch_client(self):
        self.mock_client = AsyncMock()
        with patch("services.deezer_api._client", self.mock_client):
            yield

    @pytest.mark.asyncio
    async def test_search_tracks_success(self):
        from services.deezer_api import search_tracks
        self.mock_client.get.return_value = _make_response({
            "data": [
                {"id": 1, "title": "Song 1"},
                {"id": 2, "title": "Song 2"},
            ]
        })

        result = await search_tracks("test query")
        assert len(result) == 2
        assert result[0]["title"] == "Song 1"

    @pytest.mark.asyncio
    async def test_search_tracks_respects_limit(self):
        from services.deezer_api import search_tracks
        self.mock_client.get.return_value = _make_response({
            "data": [{"id": i, "title": f"Song {i}"} for i in range(30)]
        })

        result = await search_tracks("test", limit=5)
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_search_tracks_empty_data(self):
        from services.deezer_api import search_tracks
        self.mock_client.get.return_value = _make_response({"data": []})

        result = await search_tracks("nonexistent")
        assert result == []

    @pytest.mark.asyncio
    async def test_search_tracks_no_data_key(self):
        from services.deezer_api import search_tracks
        self.mock_client.get.return_value = _make_response({"error": "quota exceeded"})

        result = await search_tracks("test")
        assert result == []

    @pytest.mark.asyncio
    async def test_search_tracks_exception_returns_none(self):
        from services.deezer_api import search_tracks
        self.mock_client.get.side_effect = httpx.HTTPError("timeout")

        result = await search_tracks("test")
        assert result is None

    @pytest.mark.asyncio
    async def test_search_tracks_http_error_returns_none(self):
        from services.deezer_api import search_tracks
        self.mock_client.get.return_value = _make_response({}, status_code=500)

        result = await search_tracks("test")
        assert result is None


class TestGetTrack:
    @pytest.fixture(autouse=True)
    def _patch_client(self):
        self.mock_client = AsyncMock()
        with patch("services.deezer_api._client", self.mock_client):
            yield

    @pytest.mark.asyncio
    async def test_get_track_success(self):
        from services.deezer_api import get_track
        self.mock_client.get.return_value = _make_response({"id": 123, "title": "My Song"})

        result = await get_track(123)
        assert result["id"] == 123
        assert result["title"] == "My Song"

    @pytest.mark.asyncio
    async def test_get_track_failure(self):
        from services.deezer_api import get_track
        self.mock_client.get.side_effect = httpx.HTTPError("not found")

        result = await get_track(999)
        assert result is None


class TestGetAlbum:
    @pytest.fixture(autouse=True)
    def _patch_client(self):
        self.mock_client = AsyncMock()
        with patch("services.deezer_api._client", self.mock_client):
            yield

    @pytest.mark.asyncio
    async def test_get_album_success(self):
        from services.deezer_api import get_album
        self.mock_client.get.return_value = _make_response({"id": 456, "title": "Album X"})

        result = await get_album(456)
        assert result["id"] == 456

    @pytest.mark.asyncio
    async def test_get_album_failure(self):
        from services.deezer_api import get_album
        self.mock_client.get.side_effect = Exception("network error")

        result = await get_album(456)
        assert result is None
