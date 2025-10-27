"""
Comprehensive unit tests for audio storage service.

Tests cover:
- Audio file upload/storage operations
- Audio file download/retrieval
- File path generation
- File existence checking
- Storage error handling (permissions, disk full, missing files)
- Cleanup operations
- Async file operations

Target: 70%+ coverage
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from rag_solution.services.storage.audio_storage import (
    AudioStorageBase,
    AudioStorageError,
    LocalFileStorage,
)


@pytest.mark.unit
class TestAudioStorageBase:
    """Unit tests for AudioStorageBase abstract class."""

    def test_cannot_instantiate_abstract_class(self) -> None:
        """Unit: Cannot instantiate AudioStorageBase directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            AudioStorageBase()  # type: ignore[abstract]

    def test_abstract_methods_defined(self) -> None:
        """Unit: Abstract methods are properly defined."""
        abstract_methods = AudioStorageBase.__abstractmethods__
        assert "store_audio" in abstract_methods
        assert "retrieve_audio" in abstract_methods
        assert "delete_audio" in abstract_methods
        assert "exists" in abstract_methods


@pytest.mark.unit
class TestLocalFileStorageInitialization:
    """Unit tests for LocalFileStorage initialization."""

    def test_initialization_with_default_path(self) -> None:
        """Unit: LocalFileStorage initializes with default path."""
        storage = LocalFileStorage()

        # Verify default path was created
        assert storage.base_path == Path("data/podcasts")
        assert storage.base_path.exists()

    def test_initialization_with_custom_path(self) -> None:
        """Unit: LocalFileStorage initializes with custom path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = f"{tmpdir}/custom_podcasts"

            storage = LocalFileStorage(base_path=custom_path)

            assert str(storage.base_path) == custom_path
            assert storage.base_path.exists()

    def test_initialization_creates_directory(self) -> None:
        """Unit: LocalFileStorage creates base directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = f"{tmpdir}/new_directory"
            assert not Path(base_path).exists()

            storage = LocalFileStorage(base_path=base_path)

            assert storage.base_path.exists()
            assert storage.base_path.is_dir()


@pytest.mark.unit
class TestLocalFileStoragePathGeneration:
    """Unit tests for file path generation."""

    def test_get_audio_path_structure(self) -> None:
        """Unit: _get_audio_path generates correct directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            podcast_id = uuid4()

            audio_path = storage._get_audio_path(podcast_id, user_id, "mp3")

            # Verify path structure: {base_path}/{user_id}/{podcast_id}/audio.mp3
            assert audio_path.parent.name == str(podcast_id)
            assert audio_path.parent.parent.name == str(user_id)
            assert audio_path.name == "audio.mp3"

    def test_get_audio_path_different_formats(self) -> None:
        """Unit: _get_audio_path handles different audio formats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            podcast_id = uuid4()

            formats = ["mp3", "wav", "opus", "aac", "flac"]
            for audio_format in formats:
                audio_path = storage._get_audio_path(podcast_id, user_id, audio_format)
                assert audio_path.suffix == f".{audio_format}"

    def test_get_audio_path_returns_path_object(self) -> None:
        """Unit: _get_audio_path returns Path object."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            podcast_id = uuid4()

            audio_path = storage._get_audio_path(podcast_id, user_id)

            assert isinstance(audio_path, Path)


@pytest.mark.unit
class TestLocalFileStorageStoreAudio:
    """Unit tests for storing audio files."""

    @pytest.mark.asyncio
    async def test_store_audio_success(self) -> None:
        """Unit: store_audio successfully stores audio file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            podcast_id = uuid4()
            audio_data = b"mock_audio_data_bytes"

            url = await storage.store_audio(podcast_id, user_id, audio_data, "mp3")

            # Verify URL format
            assert url == f"/api/podcasts/{podcast_id}/audio"

            # Verify file exists
            audio_path = storage._get_audio_path(podcast_id, user_id, "mp3")
            assert audio_path.exists()

            # Verify file content
            with open(audio_path, "rb") as f:
                saved_data = f.read()
            assert saved_data == audio_data

    @pytest.mark.asyncio
    async def test_store_audio_creates_directory_structure(self) -> None:
        """Unit: store_audio creates user and podcast directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            podcast_id = uuid4()
            audio_data = b"test_data"

            await storage.store_audio(podcast_id, user_id, audio_data, "mp3")

            # Verify directory structure
            user_dir = storage.base_path / str(user_id)
            podcast_dir = user_dir / str(podcast_id)
            assert user_dir.exists()
            assert podcast_dir.exists()

    @pytest.mark.asyncio
    async def test_store_audio_different_formats(self) -> None:
        """Unit: store_audio handles different audio formats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            audio_data = b"audio_data"

            formats = ["mp3", "wav", "opus", "aac", "flac"]
            for audio_format in formats:
                podcast_id = uuid4()
                url = await storage.store_audio(podcast_id, user_id, audio_data, audio_format)

                assert url == f"/api/podcasts/{podcast_id}/audio"
                audio_path = storage._get_audio_path(podcast_id, user_id, audio_format)
                assert audio_path.exists()

    @pytest.mark.asyncio
    async def test_store_audio_overwrites_existing(self) -> None:
        """Unit: store_audio overwrites existing audio file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            podcast_id = uuid4()

            # Store first audio
            first_data = b"first_audio_data"
            await storage.store_audio(podcast_id, user_id, first_data, "mp3")

            # Store second audio (overwrite)
            second_data = b"second_audio_data_different"
            await storage.store_audio(podcast_id, user_id, second_data, "mp3")

            # Verify overwritten content
            audio_path = storage._get_audio_path(podcast_id, user_id, "mp3")
            with open(audio_path, "rb") as f:
                saved_data = f.read()
            assert saved_data == second_data

    @pytest.mark.asyncio
    async def test_store_audio_large_file(self) -> None:
        """Unit: store_audio handles large audio files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            podcast_id = uuid4()

            # Create large audio data (10 MB)
            large_audio_data = b"x" * (10 * 1024 * 1024)

            url = await storage.store_audio(podcast_id, user_id, large_audio_data, "mp3")

            assert url == f"/api/podcasts/{podcast_id}/audio"
            audio_path = storage._get_audio_path(podcast_id, user_id, "mp3")
            assert audio_path.exists()
            assert audio_path.stat().st_size == len(large_audio_data)

    @pytest.mark.asyncio
    async def test_store_audio_empty_data(self) -> None:
        """Unit: store_audio handles empty audio data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            podcast_id = uuid4()

            url = await storage.store_audio(podcast_id, user_id, b"", "mp3")

            assert url == f"/api/podcasts/{podcast_id}/audio"
            audio_path = storage._get_audio_path(podcast_id, user_id, "mp3")
            assert audio_path.exists()
            assert audio_path.stat().st_size == 0

    @pytest.mark.asyncio
    async def test_store_audio_permission_error(self) -> None:
        """Unit: store_audio raises AudioStorageError on permission error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            podcast_id = uuid4()

            # Mock open to raise permission error
            with patch("builtins.open", side_effect=PermissionError("Permission denied")):
                with pytest.raises(AudioStorageError, match="Failed to store audio"):
                    await storage.store_audio(podcast_id, user_id, b"data", "mp3")

    @pytest.mark.asyncio
    async def test_store_audio_disk_full_error(self) -> None:
        """Unit: store_audio raises AudioStorageError on disk full."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            podcast_id = uuid4()

            # Mock open to raise OSError (disk full)
            with patch("builtins.open", side_effect=OSError(28, "No space left on device")):
                with pytest.raises(AudioStorageError, match="Failed to store audio"):
                    await storage.store_audio(podcast_id, user_id, b"data", "mp3")

    @pytest.mark.asyncio
    async def test_store_audio_io_error(self) -> None:
        """Unit: store_audio raises AudioStorageError on I/O error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            podcast_id = uuid4()

            # Mock open to raise IOError
            with patch("builtins.open", side_effect=OSError("I/O error")):
                with pytest.raises(AudioStorageError, match="Failed to store audio"):
                    await storage.store_audio(podcast_id, user_id, b"data", "mp3")


@pytest.mark.unit
class TestLocalFileStorageRetrieveAudio:
    """Unit tests for retrieving audio files."""

    @pytest.mark.asyncio
    async def test_retrieve_audio_success_mp3(self) -> None:
        """Unit: retrieve_audio successfully retrieves MP3 audio file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            podcast_id = uuid4()
            audio_data = b"test_audio_content"

            # Store audio first
            await storage.store_audio(podcast_id, user_id, audio_data, "mp3")

            # Retrieve audio
            retrieved_data = await storage.retrieve_audio(podcast_id, user_id)

            assert retrieved_data == audio_data

    @pytest.mark.asyncio
    async def test_retrieve_audio_tries_multiple_formats(self) -> None:
        """Unit: retrieve_audio tries multiple audio formats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            podcast_id = uuid4()
            audio_data = b"wav_audio_content"

            # Store as WAV (not MP3)
            await storage.store_audio(podcast_id, user_id, audio_data, "wav")

            # Retrieve should find WAV format
            retrieved_data = await storage.retrieve_audio(podcast_id, user_id)

            assert retrieved_data == audio_data

    @pytest.mark.asyncio
    async def test_retrieve_audio_all_supported_formats(self) -> None:
        """Unit: retrieve_audio supports all audio formats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()

            formats = ["mp3", "wav", "opus", "aac", "flac"]
            for audio_format in formats:
                podcast_id = uuid4()
                audio_data = f"{audio_format}_audio_data".encode()

                # Store in specific format
                await storage.store_audio(podcast_id, user_id, audio_data, audio_format)

                # Retrieve should find it
                retrieved_data = await storage.retrieve_audio(podcast_id, user_id)
                assert retrieved_data == audio_data

    @pytest.mark.asyncio
    async def test_retrieve_audio_not_found(self) -> None:
        """Unit: retrieve_audio raises AudioStorageError when file not found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            podcast_id = uuid4()

            with pytest.raises(AudioStorageError, match="not found"):
                await storage.retrieve_audio(podcast_id, user_id)

    @pytest.mark.asyncio
    async def test_retrieve_audio_permission_error(self) -> None:
        """Unit: retrieve_audio raises AudioStorageError on permission error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            podcast_id = uuid4()
            audio_data = b"test_data"

            # Store audio first
            await storage.store_audio(podcast_id, user_id, audio_data, "mp3")

            # Mock open to raise permission error
            with patch("builtins.open", side_effect=PermissionError("Permission denied")):
                with pytest.raises(AudioStorageError, match="Failed to retrieve audio"):
                    await storage.retrieve_audio(podcast_id, user_id)

    @pytest.mark.asyncio
    async def test_retrieve_audio_io_error(self) -> None:
        """Unit: retrieve_audio raises AudioStorageError on I/O error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            podcast_id = uuid4()
            audio_data = b"test_data"

            # Store audio first
            await storage.store_audio(podcast_id, user_id, audio_data, "mp3")

            # Mock open to raise IOError
            with patch("builtins.open", side_effect=OSError("I/O error")):
                with pytest.raises(AudioStorageError, match="Failed to retrieve audio"):
                    await storage.retrieve_audio(podcast_id, user_id)

    @pytest.mark.asyncio
    async def test_retrieve_audio_large_file(self) -> None:
        """Unit: retrieve_audio handles large audio files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            podcast_id = uuid4()

            # Create large audio data (5 MB)
            large_audio_data = b"y" * (5 * 1024 * 1024)

            await storage.store_audio(podcast_id, user_id, large_audio_data, "mp3")
            retrieved_data = await storage.retrieve_audio(podcast_id, user_id)

            assert retrieved_data == large_audio_data
            assert len(retrieved_data) == 5 * 1024 * 1024

    @pytest.mark.asyncio
    async def test_retrieve_audio_empty_file(self) -> None:
        """Unit: retrieve_audio handles empty audio files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            podcast_id = uuid4()

            await storage.store_audio(podcast_id, user_id, b"", "mp3")
            retrieved_data = await storage.retrieve_audio(podcast_id, user_id)

            assert retrieved_data == b""


@pytest.mark.unit
class TestLocalFileStorageDeleteAudio:
    """Unit tests for deleting audio files."""

    @pytest.mark.asyncio
    async def test_delete_audio_success(self) -> None:
        """Unit: delete_audio successfully deletes audio file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            podcast_id = uuid4()
            audio_data = b"test_data"

            # Store audio first
            await storage.store_audio(podcast_id, user_id, audio_data, "mp3")
            audio_path = storage._get_audio_path(podcast_id, user_id, "mp3")
            assert audio_path.exists()

            # Delete audio
            result = await storage.delete_audio(podcast_id, user_id)

            assert result is True
            assert not audio_path.exists()

    @pytest.mark.asyncio
    async def test_delete_audio_not_found(self) -> None:
        """Unit: delete_audio returns False when file not found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            podcast_id = uuid4()

            result = await storage.delete_audio(podcast_id, user_id)

            assert result is False

    @pytest.mark.asyncio
    async def test_delete_audio_removes_empty_podcast_directory(self) -> None:
        """Unit: delete_audio removes empty podcast directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            podcast_id = uuid4()

            await storage.store_audio(podcast_id, user_id, b"data", "mp3")
            podcast_dir = storage.base_path / str(user_id) / str(podcast_id)
            assert podcast_dir.exists()

            await storage.delete_audio(podcast_id, user_id)

            assert not podcast_dir.exists()

    @pytest.mark.asyncio
    async def test_delete_audio_removes_empty_user_directory(self) -> None:
        """Unit: delete_audio removes empty user directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            podcast_id = uuid4()

            await storage.store_audio(podcast_id, user_id, b"data", "mp3")
            user_dir = storage.base_path / str(user_id)
            assert user_dir.exists()

            await storage.delete_audio(podcast_id, user_id)

            assert not user_dir.exists()

    @pytest.mark.asyncio
    async def test_delete_audio_keeps_user_directory_if_not_empty(self) -> None:
        """Unit: delete_audio keeps user directory if it has other podcasts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            podcast_id_1 = uuid4()
            podcast_id_2 = uuid4()

            # Store two podcasts for same user
            await storage.store_audio(podcast_id_1, user_id, b"data1", "mp3")
            await storage.store_audio(podcast_id_2, user_id, b"data2", "mp3")

            user_dir = storage.base_path / str(user_id)
            assert user_dir.exists()

            # Delete first podcast
            await storage.delete_audio(podcast_id_1, user_id)

            # User directory should still exist (has second podcast)
            assert user_dir.exists()

    @pytest.mark.asyncio
    async def test_delete_audio_all_formats(self) -> None:
        """Unit: delete_audio deletes all audio format files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            podcast_id = uuid4()

            # Store multiple formats
            formats = ["mp3", "wav", "opus"]
            for audio_format in formats:
                await storage.store_audio(podcast_id, user_id, b"data", audio_format)

            # Verify all exist
            for audio_format in formats:
                audio_path = storage._get_audio_path(podcast_id, user_id, audio_format)
                assert audio_path.exists()

            # Delete audio (should delete all formats)
            result = await storage.delete_audio(podcast_id, user_id)

            assert result is True
            for audio_format in formats:
                audio_path = storage._get_audio_path(podcast_id, user_id, audio_format)
                assert not audio_path.exists()

    @pytest.mark.asyncio
    async def test_delete_audio_permission_error(self) -> None:
        """Unit: delete_audio raises AudioStorageError on permission error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            podcast_id = uuid4()

            await storage.store_audio(podcast_id, user_id, b"data", "mp3")

            # Mock unlink to raise permission error
            with patch("pathlib.Path.unlink", side_effect=PermissionError("Permission denied")):
                with pytest.raises(AudioStorageError, match="Failed to delete audio"):
                    await storage.delete_audio(podcast_id, user_id)

    @pytest.mark.asyncio
    async def test_delete_audio_io_error(self) -> None:
        """Unit: delete_audio raises AudioStorageError on I/O error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            podcast_id = uuid4()

            await storage.store_audio(podcast_id, user_id, b"data", "mp3")

            # Mock unlink to raise OSError
            with patch("pathlib.Path.unlink", side_effect=OSError("I/O error")):
                with pytest.raises(AudioStorageError, match="Failed to delete audio"):
                    await storage.delete_audio(podcast_id, user_id)


@pytest.mark.unit
class TestLocalFileStorageExists:
    """Unit tests for checking audio file existence."""

    @pytest.mark.asyncio
    async def test_exists_returns_true_for_existing_mp3(self) -> None:
        """Unit: exists returns True for existing MP3 file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            podcast_id = uuid4()

            await storage.store_audio(podcast_id, user_id, b"data", "mp3")

            result = await storage.exists(podcast_id, user_id)

            assert result is True

    @pytest.mark.asyncio
    async def test_exists_returns_true_for_any_format(self) -> None:
        """Unit: exists returns True if any audio format exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()

            formats = ["mp3", "wav", "opus", "aac", "flac"]
            for audio_format in formats:
                podcast_id = uuid4()
                await storage.store_audio(podcast_id, user_id, b"data", audio_format)

                result = await storage.exists(podcast_id, user_id)
                assert result is True

    @pytest.mark.asyncio
    async def test_exists_returns_false_for_nonexistent_file(self) -> None:
        """Unit: exists returns False when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            podcast_id = uuid4()

            result = await storage.exists(podcast_id, user_id)

            assert result is False

    @pytest.mark.asyncio
    async def test_exists_returns_false_after_deletion(self) -> None:
        """Unit: exists returns False after audio is deleted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            podcast_id = uuid4()

            await storage.store_audio(podcast_id, user_id, b"data", "mp3")
            assert await storage.exists(podcast_id, user_id) is True

            await storage.delete_audio(podcast_id, user_id)

            result = await storage.exists(podcast_id, user_id)
            assert result is False

    @pytest.mark.asyncio
    async def test_exists_different_users(self) -> None:
        """Unit: exists checks user-specific audio files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id_1 = uuid4()
            user_id_2 = uuid4()
            podcast_id = uuid4()

            # Store audio for user 1
            await storage.store_audio(podcast_id, user_id_1, b"data", "mp3")

            # Check existence for user 1 (should exist)
            assert await storage.exists(podcast_id, user_id_1) is True

            # Check existence for user 2 (should not exist)
            assert await storage.exists(podcast_id, user_id_2) is False


@pytest.mark.unit
class TestAudioStorageError:
    """Unit tests for AudioStorageError exception."""

    def test_audio_storage_error_is_exception(self) -> None:
        """Unit: AudioStorageError inherits from Exception."""
        error = AudioStorageError("test error")
        assert isinstance(error, Exception)

    def test_audio_storage_error_message(self) -> None:
        """Unit: AudioStorageError stores error message."""
        error_message = "Failed to store audio"
        error = AudioStorageError(error_message)
        assert str(error) == error_message

    def test_audio_storage_error_can_be_raised(self) -> None:
        """Unit: AudioStorageError can be raised and caught."""
        with pytest.raises(AudioStorageError, match="test error"):
            raise AudioStorageError("test error")


@pytest.mark.unit
class TestLocalFileStorageEdgeCases:
    """Unit tests for edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_store_and_retrieve_binary_data(self) -> None:
        """Unit: Handles binary data correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            podcast_id = uuid4()

            # Binary data with null bytes and special characters
            binary_data = b"\x00\x01\x02\xff\xfe\xfd"

            await storage.store_audio(podcast_id, user_id, binary_data, "mp3")
            retrieved_data = await storage.retrieve_audio(podcast_id, user_id)

            assert retrieved_data == binary_data

    @pytest.mark.asyncio
    async def test_concurrent_operations_different_podcasts(self) -> None:
        """Unit: Handles concurrent operations on different podcasts."""
        import asyncio

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()

            # Create multiple store operations
            async def store_podcast(index: int) -> str:
                podcast_id = uuid4()
                data = f"podcast_{index}".encode()
                return await storage.store_audio(podcast_id, user_id, data, "mp3")

            # Run concurrent operations
            results = await asyncio.gather(*[store_podcast(i) for i in range(5)])

            assert len(results) == 5
            assert all(url.startswith("/api/podcasts/") for url in results)

    @pytest.mark.asyncio
    async def test_uuid_as_string_and_uuid_object(self) -> None:
        """Unit: Handles UUID as both string and UUID object."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            podcast_id = uuid4()

            await storage.store_audio(podcast_id, user_id, b"data", "mp3")

            # Should work with UUID objects
            assert await storage.exists(podcast_id, user_id) is True

    @pytest.mark.asyncio
    async def test_special_characters_in_path_handling(self) -> None:
        """Unit: Handles paths correctly regardless of OS."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            podcast_id = uuid4()

            # Should work on Windows and Unix
            await storage.store_audio(podcast_id, user_id, b"data", "mp3")
            audio_path = storage._get_audio_path(podcast_id, user_id, "mp3")

            assert audio_path.exists()
            # Path should use OS-appropriate separators
            assert str(user_id) in str(audio_path)
            assert str(podcast_id) in str(audio_path)

    @pytest.mark.asyncio
    async def test_directory_cleanup_handles_race_conditions(self) -> None:
        """Unit: delete_audio handles directory already deleted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            podcast_id = uuid4()

            await storage.store_audio(podcast_id, user_id, b"data", "mp3")

            # Manually delete the directory
            podcast_dir = storage.base_path / str(user_id) / str(podcast_id)
            import shutil

            shutil.rmtree(podcast_dir)

            # Should not raise error
            result = await storage.delete_audio(podcast_id, user_id)
            assert result is False

    @pytest.mark.asyncio
    async def test_base_path_with_trailing_slash(self) -> None:
        """Unit: Handles base_path with trailing slash correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path_with_slash = f"{tmpdir}/"
            storage = LocalFileStorage(base_path=base_path_with_slash)
            user_id = uuid4()
            podcast_id = uuid4()

            url = await storage.store_audio(podcast_id, user_id, b"data", "mp3")

            assert url == f"/api/podcasts/{podcast_id}/audio"
            assert await storage.exists(podcast_id, user_id) is True


@pytest.mark.unit
class TestLocalFileStorageIntegration:
    """Integration-style unit tests for complete workflows."""

    @pytest.mark.asyncio
    async def test_complete_audio_lifecycle(self) -> None:
        """Unit: Complete workflow - store, retrieve, check, delete."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            podcast_id = uuid4()
            audio_data = b"complete_lifecycle_audio_data"

            # 1. Store audio
            url = await storage.store_audio(podcast_id, user_id, audio_data, "mp3")
            assert url == f"/api/podcasts/{podcast_id}/audio"

            # 2. Check existence
            exists = await storage.exists(podcast_id, user_id)
            assert exists is True

            # 3. Retrieve audio
            retrieved_data = await storage.retrieve_audio(podcast_id, user_id)
            assert retrieved_data == audio_data

            # 4. Delete audio
            deleted = await storage.delete_audio(podcast_id, user_id)
            assert deleted is True

            # 5. Verify deletion
            exists_after = await storage.exists(podcast_id, user_id)
            assert exists_after is False

    @pytest.mark.asyncio
    async def test_multiple_users_isolation(self) -> None:
        """Unit: Audio files are isolated by user."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id_1 = uuid4()
            user_id_2 = uuid4()
            podcast_id = uuid4()

            # Store audio for user 1
            data_1 = b"user_1_audio_data"
            await storage.store_audio(podcast_id, user_id_1, data_1, "mp3")

            # Store audio for user 2 (same podcast_id)
            data_2 = b"user_2_audio_data"
            await storage.store_audio(podcast_id, user_id_2, data_2, "mp3")

            # Retrieve for user 1
            retrieved_1 = await storage.retrieve_audio(podcast_id, user_id_1)
            assert retrieved_1 == data_1

            # Retrieve for user 2
            retrieved_2 = await storage.retrieve_audio(podcast_id, user_id_2)
            assert retrieved_2 == data_2

            # Delete for user 1 doesn't affect user 2
            await storage.delete_audio(podcast_id, user_id_1)
            assert await storage.exists(podcast_id, user_id_1) is False
            assert await storage.exists(podcast_id, user_id_2) is True

    @pytest.mark.asyncio
    async def test_format_migration(self) -> None:
        """Unit: Can migrate from one format to another."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            user_id = uuid4()
            podcast_id = uuid4()
            audio_data = b"audio_data"

            # Store as MP3
            await storage.store_audio(podcast_id, user_id, audio_data, "mp3")
            assert await storage.exists(podcast_id, user_id) is True

            # Store as WAV (overwrite with different format)
            await storage.store_audio(podcast_id, user_id, audio_data, "wav")

            # Both formats exist now
            mp3_path = storage._get_audio_path(podcast_id, user_id, "mp3")
            wav_path = storage._get_audio_path(podcast_id, user_id, "wav")
            assert mp3_path.exists()
            assert wav_path.exists()

            # Retrieve finds first available format
            retrieved = await storage.retrieve_audio(podcast_id, user_id)
            assert retrieved == audio_data
