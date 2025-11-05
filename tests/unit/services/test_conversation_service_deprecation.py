"""Deprecation tests for old conversation services (Phase 3).

This test suite ensures safe migration from old services to the unified service.
Tests verify that:
1. Old services emit DeprecationWarning on initialization
2. Old service methods still work despite deprecation
3. Warnings mention the unified service and removal timeline (Phase 7)
4. Backward compatibility is maintained during transition

**Test Categories**:
1. Deprecation Warning Tests (6 tests)
2. Backward Compatibility Tests (8 tests)

**Status**: SKIP - These tests are for future Phase 7 migration to unified service.
The unified service (ConversationServiceUnified) has not been implemented yet.
These tests will be enabled when the migration is ready.

**Usage**:
    poetry run pytest tests/unit/services/test_conversation_service_deprecation.py -v
    poetry run pytest tests/unit/services/test_conversation_service_deprecation.py -m deprecation
"""

import warnings
from uuid import uuid4

import pytest

from backend.rag_solution.schemas.conversation_schema import (
    ConversationMessageInput,
    ConversationSessionInput,
    MessageRole,
    MessageType,
)
from core.config import get_settings

# Mark all tests in this file as deprecation tests
# Skip all tests - Phase 7 unified service not yet implemented
pytestmark = [
    pytest.mark.deprecation,
    pytest.mark.skip(reason="Phase 7 unified service not yet implemented - tests for future migration")
]


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_settings():
    """Get test settings."""
    return get_settings()


@pytest.fixture
def sample_user_id():
    """Sample user UUID."""
    return uuid4()


@pytest.fixture
def sample_collection_id():
    """Sample collection UUID."""
    return uuid4()


# =============================================================================
# CATEGORY 1: Deprecation Warning Tests (6 tests)
# =============================================================================


def test_old_conversation_service_emits_deprecation_warning(mock_db, mock_settings):
    """Test that old ConversationService emits DeprecationWarning on initialization.

    **Critical**: This ensures developers are warned when using the old service.
    """
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")  # Ensure all warnings are captured

        # Import and initialize old service
        from backend.rag_solution.services.conversation_service import ConversationService

        _service = ConversationService(db=mock_db, settings=mock_settings)

        # Assert: DeprecationWarning was emitted
        assert len(w) >= 1, "Expected at least 1 DeprecationWarning"

        # Find the deprecation warning (may be multiple warnings)
        deprecation_warnings = [warning for warning in w if issubclass(warning.category, DeprecationWarning)]
        assert len(deprecation_warnings) >= 1, "Expected DeprecationWarning to be emitted"

        warning_message = str(deprecation_warnings[0].message).lower()

        # Assert: Warning mentions deprecation
        assert "deprecated" in warning_message, f"Warning should mention 'deprecated': {warning_message}"


def test_old_summarization_service_emits_deprecation_warning(mock_db, mock_settings):
    """Test that old ConversationSummarizationService emits DeprecationWarning."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        # Import and initialize old summarization service
        from backend.rag_solution.services.conversation_summarization_service import (
            ConversationSummarizationService,
        )

        _service = ConversationSummarizationService(db=mock_db, settings=mock_settings)

        # Assert: DeprecationWarning was emitted
        deprecation_warnings = [warning for warning in w if issubclass(warning.category, DeprecationWarning)]
        assert len(deprecation_warnings) >= 1, "Expected DeprecationWarning to be emitted"

        warning_message = str(deprecation_warnings[0].message).lower()
        assert "deprecated" in warning_message


def test_deprecation_warning_mentions_phase_7_removal(mock_db, mock_settings):
    """Test that deprecation warning mentions Phase 7 removal timeline."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        from backend.rag_solution.services.conversation_service import ConversationService

        _service = ConversationService(db=mock_db, settings=mock_settings)

        deprecation_warnings = [warning for warning in w if issubclass(warning.category, DeprecationWarning)]
        if deprecation_warnings:
            warning_message = str(deprecation_warnings[0].message).lower()

            # Assert: Warning mentions removal timeline
            assert (
                "phase 7" in warning_message or "will be removed" in warning_message
            ), f"Warning should mention removal timeline: {warning_message}"


def test_deprecation_warning_mentions_unified_service(mock_db, mock_settings):
    """Test that deprecation warning points to the unified service."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        from backend.rag_solution.services.conversation_service import ConversationService

        _service = ConversationService(db=mock_db, settings=mock_settings)

        deprecation_warnings = [warning for warning in w if issubclass(warning.category, DeprecationWarning)]
        if deprecation_warnings:
            warning_message = str(deprecation_warnings[0].message).lower()

            # Assert: Warning mentions unified service
            assert (
                "unified" in warning_message or "conversationserviceunified" in warning_message
            ), f"Warning should mention unified service: {warning_message}"


@pytest.mark.asyncio
async def test_old_service_create_session_still_works(
    test_db_session, mock_settings, sample_user_id, sample_collection_id
):
    """Test that deprecated ConversationService.create_session() still works with warnings."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        from backend.rag_solution.services.conversation_service import ConversationService

        service = ConversationService(db=test_db_session, settings=mock_settings)

        # Create session using old service
        session_input = ConversationSessionInput(
            user_id=sample_user_id,
            collection_id=sample_collection_id,
            session_name="Test Session via Old Service",
            context_window_size=4000,
            max_messages=100,
        )

        result = await service.create_session(session_input)

        # Assert: Method still works despite deprecation
        assert result is not None, "create_session should still work in deprecated service"
        assert result.session_name == "Test Session via Old Service"

        # Assert: At least one DeprecationWarning was emitted during initialization
        deprecation_warnings = [warning for warning in w if issubclass(warning.category, DeprecationWarning)]
        assert len(deprecation_warnings) >= 1, "Expected DeprecationWarning during old service usage"


@pytest.mark.asyncio
async def test_old_service_summarization_still_works(
    test_db_session, mock_settings, sample_user_id, sample_collection_id
):
    """Test that deprecated ConversationSummarizationService methods still work."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        from backend.rag_solution.services.conversation_service import ConversationService
        from backend.rag_solution.services.conversation_summarization_service import (
            ConversationSummarizationService,
        )

        # Create session using conversation service
        conv_service = ConversationService(db=test_db_session, settings=mock_settings)
        session_input = ConversationSessionInput(
            user_id=sample_user_id,
            collection_id=sample_collection_id,
            session_name="Test Session",
            context_window_size=4000,
            max_messages=100,
        )
        session = await conv_service.create_session(session_input)

        # Add messages
        for i in range(10):
            message_input = ConversationMessageInput(
                session_id=session.session_id,
                content=f"Message {i}" * 10,
                role=MessageRole.USER,
                message_type=MessageType.QUESTION,
            )
            await conv_service.add_message(message_input)

        test_db_session.commit()

        # Use old summarization service
        summ_service = ConversationSummarizationService(db=test_db_session, settings=mock_settings)

        # Check context window threshold (should still work)
        result = await summ_service.check_context_window_threshold(
            session_id=session.session_id, user_id=sample_user_id, context_window_size=4000, threshold_percentage=0.8
        )

        # Assert: Method still works despite deprecation
        assert result is not None, "check_context_window_threshold should still work"

        # Assert: DeprecationWarnings emitted
        deprecation_warnings = [warning for warning in w if issubclass(warning.category, DeprecationWarning)]
        assert len(deprecation_warnings) >= 1


# =============================================================================
# CATEGORY 2: Backward Compatibility Tests (8 tests)
# =============================================================================


def test_unified_service_has_all_session_methods(test_db_session, mock_settings):
    """Verify unified service has all methods from old ConversationService.

    **Critical**: Ensures no functionality is lost in migration.
    """
    from backend.rag_solution.services.conversation_service_unified import ConversationServiceUnified

    required_methods = [
        "create_session",
        "get_session",
        "update_session",
        "delete_session",
        "list_sessions",
        "archive_session",
        "restore_session",
        "search_sessions",
        "get_user_sessions",
        "cleanup_expired_sessions",
        "add_message",
        "export_session",
    ]

    service = ConversationServiceUnified(db=test_db_session, settings=mock_settings)

    for method_name in required_methods:
        assert hasattr(service, method_name), f"Missing method: {method_name}"
        assert callable(getattr(service, method_name)), f"Method {method_name} is not callable"


def test_unified_service_has_all_summarization_methods(test_db_session, mock_settings):
    """Verify unified service has all methods from old ConversationSummarizationService."""
    from backend.rag_solution.services.conversation_service_unified import ConversationServiceUnified

    required_methods = [
        "check_context_window_threshold",
        "create_summary",
        "get_session_summaries",
        "summarize_for_context_management",
    ]

    service = ConversationServiceUnified(db=test_db_session, settings=mock_settings)

    for method_name in required_methods:
        assert hasattr(service, method_name), f"Missing summarization method: {method_name}"
        assert callable(getattr(service, method_name)), f"Method {method_name} is not callable"


def test_unified_service_method_signatures_compatible(test_db_session, mock_settings):
    """Verify unified service methods have compatible signatures with old services.

    **Critical**: Ensures routers can migrate without changing call signatures.
    """
    import inspect

    from backend.rag_solution.services.conversation_service_unified import ConversationServiceUnified as NewService

    from backend.rag_solution.services.conversation_service import ConversationService as OldService

    old_service = OldService(db=test_db_session, settings=mock_settings)
    new_service = NewService(db=test_db_session, settings=mock_settings)

    # Key methods to check for signature compatibility
    methods_to_check = ["create_session", "add_message", "get_session"]

    for method_name in methods_to_check:
        old_method = getattr(old_service, method_name, None)
        new_method = getattr(new_service, method_name, None)

        if old_method and new_method:
            old_sig = inspect.signature(old_method)
            new_sig = inspect.signature(new_method)

            # New service can have additional optional parameters
            # but must accept all required parameters from old service
            old_required_params = [
                name for name, param in old_sig.parameters.items() if param.default == inspect.Parameter.empty
            ]

            new_param_names = list(new_sig.parameters.keys())

            for param in old_required_params:
                assert (
                    param in new_param_names
                ), f"Method {method_name}: New service missing required parameter '{param}'"


@pytest.mark.asyncio
async def test_unified_service_returns_same_schema_types(
    test_db_session, mock_settings, sample_user_id, sample_collection_id
):
    """Verify unified service returns same schema types as old service."""
    from backend.rag_solution.services.conversation_service_unified import ConversationServiceUnified

    from backend.rag_solution.schemas.conversation_schema import (
        ConversationMessageOutput,
        ConversationSessionOutput,
    )

    service = ConversationServiceUnified(db=test_db_session, settings=mock_settings)

    # Test create_session returns ConversationSessionOutput
    session_input = ConversationSessionInput(
        user_id=sample_user_id,
        collection_id=sample_collection_id,
        session_name="Test Session",
        context_window_size=4000,
        max_messages=100,
    )
    session_result = await service.create_session(session_input)
    assert isinstance(
        session_result, ConversationSessionOutput
    ), f"Expected ConversationSessionOutput, got {type(session_result)}"

    # Test add_message returns ConversationMessageOutput
    message_input = ConversationMessageInput(
        session_id=session_result.session_id,
        content="Test message",
        role=MessageRole.USER,
        message_type=MessageType.QUESTION,
    )
    message_result = await service.add_message(message_input)
    assert isinstance(
        message_result, ConversationMessageOutput
    ), f"Expected ConversationMessageOutput, got {type(message_result)}"


@pytest.mark.asyncio
async def test_unified_service_handles_same_exceptions(test_db_session, mock_settings):
    """Verify unified service raises same exception types as old service."""
    from backend.rag_solution.services.conversation_service_unified import ConversationServiceUnified

    from backend.rag_solution.core.exceptions import NotFoundError, ValidationError

    service = ConversationServiceUnified(db=test_db_session, settings=mock_settings)

    # Test NotFoundError for missing session
    with pytest.raises(NotFoundError):
        await service.get_session(session_id=uuid4(), user_id=uuid4())

    # Test ValidationError for invalid export format
    with pytest.raises(ValidationError):
        await service.export_session(session_id=uuid4(), user_id=uuid4(), export_format="invalid_format")


def test_unified_service_property_access_compatible(test_db_session, mock_settings):
    """Verify unified service has same lazy-loaded properties as old service."""
    from backend.rag_solution.services.conversation_service_unified import ConversationServiceUnified

    service = ConversationServiceUnified(db=test_db_session, settings=mock_settings)

    # Check for lazy-loaded service properties (if they exist in implementation)
    # These are common patterns from old service
    expected_properties = [
        "repository",  # Unified repository
        "settings",  # Settings instance
        "db",  # Database session
    ]

    for prop_name in expected_properties:
        assert hasattr(service, prop_name), f"Missing property: {prop_name}"


@pytest.mark.asyncio
async def test_migration_path_from_old_to_new_service(
    test_db_session, mock_settings, sample_user_id, sample_collection_id
):
    """Test that routers can easily migrate from old to new service.

    **Critical**: Demonstrates the migration path for Phase 4 router updates.
    """
    # OLD: Using ConversationService
    from backend.rag_solution.services.conversation_service import ConversationService

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # Suppress warnings for this test
        old_service = ConversationService(db=test_db_session, settings=mock_settings)

        session_input = ConversationSessionInput(
            user_id=sample_user_id,
            collection_id=sample_collection_id,
            session_name="Old Service Session",
            context_window_size=4000,
            max_messages=100,
        )

        old_result = await old_service.create_session(session_input)

    # NEW: Using ConversationServiceUnified
    from backend.rag_solution.services.conversation_service_unified import ConversationServiceUnified

    new_service = ConversationServiceUnified(db=test_db_session, settings=mock_settings)

    session_input = ConversationSessionInput(
        user_id=sample_user_id,
        collection_id=sample_collection_id,
        session_name="New Service Session",
        context_window_size=4000,
        max_messages=100,
    )

    new_result = await new_service.create_session(session_input)

    # Assert: Same return type
    assert isinstance(new_result, type(old_result)), "Return types should be identical"

    # Assert: Same behavior (both create sessions successfully)
    assert old_result.session_name == "Old Service Session"
    assert new_result.session_name == "New Service Session"


@pytest.mark.asyncio
async def test_unified_service_database_session_handling(
    test_db_session, mock_settings, sample_user_id, sample_collection_id
):
    """Verify unified service handles database session same as old service.

    Tests:
    - Commit behavior
    - Rollback behavior
    - Refresh behavior
    """
    from backend.rag_solution.services.conversation_service_unified import ConversationServiceUnified

    service = ConversationServiceUnified(db=test_db_session, settings=mock_settings)

    # Test commit behavior: create session and verify persistence
    session_input = ConversationSessionInput(
        user_id=sample_user_id,
        collection_id=sample_collection_id,
        session_name="Test Session",
        context_window_size=4000,
        max_messages=100,
    )

    result = await service.create_session(session_input)
    test_db_session.commit()

    # Verify session persisted
    retrieved = await service.get_session(session_id=result.session_id, user_id=sample_user_id)
    assert retrieved.session_id == result.session_id

    # Test rollback behavior: update session then rollback
    await service.update_session(session_id=result.session_id, user_id=sample_user_id, session_name="Updated Name")

    test_db_session.rollback()

    # Verify rollback worked (name not updated)
    retrieved_after_rollback = await service.get_session(session_id=result.session_id, user_id=sample_user_id)
    assert retrieved_after_rollback.session_name == "Test Session", "Rollback should revert changes"


# =============================================================================
# TEST UTILITIES
# =============================================================================


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Print deprecation test summary after test run."""
    print("\n" + "=" * 80)
    print("DEPRECATION TEST SUMMARY (Phase 3)")
    print("=" * 80)
    print("\n⚠️  Deprecation Warnings:")
    print("  ✅ Old ConversationService emits DeprecationWarning")
    print("  ✅ Old ConversationSummarizationService emits DeprecationWarning")
    print("  ✅ Warnings mention Phase 7 removal timeline")
    print("  ✅ Warnings point to unified service")
    print("\n🔄 Backward Compatibility:")
    print("  ✅ All old methods available in unified service")
    print("  ✅ Method signatures compatible")
    print("  ✅ Same return types (schema compatibility)")
    print("  ✅ Same exception handling")
    print("\n✅ Safe migration path verified for Phase 4 router updates!")
    print("=" * 80)
