"""Quick test to verify ElevenLabs API key works."""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def test_elevenlabs_api():
    """Test ElevenLabs API key by listing voices."""
    api_key = os.getenv("ELEVENLABS_API_KEY")

    if not api_key:
        print("❌ ELEVENLABS_API_KEY not found in environment")
        return False

    print(f"✅ API Key loaded: {api_key[:15]}...{api_key[-4:]}")
    print(f"   Length: {len(api_key)} characters")

    # Test API call
    async with httpx.AsyncClient(
        base_url="https://api.elevenlabs.io/v1",
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
        },
        timeout=30.0,
    ) as client:
        try:
            print("\n🔄 Testing ElevenLabs API (GET /voices)...")
            response = await client.get("/voices")

            print(f"   Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                voices = data.get("voices", [])
                print("✅ API call successful!")
                print(f"   Found {len(voices)} voices")
                if voices:
                    print(f"   First voice: {voices[0]['name']} (ID: {voices[0]['voice_id']})")
                return True
            else:
                print(f"❌ API call failed: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return False

        except Exception as e:
            print(f"❌ Error: {e}")
            return False


if __name__ == "__main__":
    result = asyncio.run(test_elevenlabs_api())
    sys.exit(0 if result else 1)
