import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestPodcastApi:
    @pytest.mark.asyncio
    async def test_get_voice_preview_success(self, client: AsyncClient) -> None:
        """Integration: Test /voice-preview endpoint returns audio for a valid voice."""
        voice_id = "alloy"  # A known valid voice from OpenAI provider
        response = await client.get(f"/api/podcasts/voice-preview/{voice_id}")

        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/mpeg"
        assert len(response.content) > 0

    @pytest.mark.asyncio
    async def test_get_voice_preview_invalid_voice(self, client: AsyncClient) -> None:
        """Integration: Test /voice-preview endpoint returns 400 for an invalid voice."""
        voice_id = "invalid_voice"
        response = await client.get(f"/api/podcasts/voice-preview/{voice_id}")

        assert response.status_code == 400
        assert "Invalid voice_id" in response.json()["detail"]