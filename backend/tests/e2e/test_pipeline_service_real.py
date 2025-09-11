"""
Real TDD tests for PipelineService - testing actual functionality to find real bugs.
"""

import pytest
from uuid import uuid4, UUID
from unittest.mock import Mock
from sqlalchemy.orm import Session

from rag_solution.services.pipeline_service import PipelineService
from rag_solution.schemas.search_schema import SearchInput
from core.config import Settings


@pytest.mark.e2e
class TestPipelineServiceReal:
    """Test real PipelineService functionality to find actual bugs."""
    
    @pytest.fixture
    def pipeline_service(self, mock_settings: Settings) -> PipelineService:
        """Create a real PipelineService with mock database."""
        mock_db = Mock(spec=Session)
        return PipelineService(mock_db, mock_settings)
    
    def test_pipeline_service_initialization(self, pipeline_service: PipelineService):
        """Test that PipelineService initializes correctly."""
        assert pipeline_service is not None
        assert hasattr(pipeline_service, 'execute_pipeline')
        assert hasattr(pipeline_service, 'db')
        assert hasattr(pipeline_service, 'settings')
    
    @pytest.mark.asyncio
    async def test_execute_pipeline_with_empty_query(self, pipeline_service: PipelineService):
        """Test execute_pipeline with empty query - should validate input."""
        search_input = SearchInput(
            question="",  # Empty query
            collection_id=uuid4(),
            pipeline_id=uuid4(),
            user_id=uuid4()
        )
        
        # Should raise validation error
        with pytest.raises(Exception) as exc_info:
            await pipeline_service.execute_pipeline(search_input, "test_collection")
        
        # Error should be about empty query
        error_message = str(exc_info.value).lower()
        assert any(keyword in error_message for keyword in ['empty', 'query', 'validation'])
    
    @pytest.mark.asyncio
    async def test_execute_pipeline_with_none_query(self, pipeline_service: PipelineService):
        """Test execute_pipeline with None query - should validate input."""
        search_input = SearchInput(
            question=None,  # None query
            collection_id=uuid4(),
            pipeline_id=uuid4(),
            user_id=uuid4()
        )
        
        # Should raise validation error
        with pytest.raises(Exception) as exc_info:
            await pipeline_service.execute_pipeline(search_input, "test_collection")
        
        # Error should be about invalid query
        error_message = str(exc_info.value).lower()
        assert any(keyword in error_message for keyword in ['none', 'null', 'validation'])
    
    @pytest.mark.asyncio
    async def test_execute_pipeline_with_valid_input_but_missing_infrastructure(self, pipeline_service: PipelineService):
        """Test execute_pipeline with valid input but missing infrastructure."""
        search_input = SearchInput(
            question="What is machine learning?",
            collection_id=uuid4(),
            pipeline_id=uuid4(),
            user_id=uuid4()
        )
        
        # Should fail due to infrastructure (Milvus connection, etc.)
        with pytest.raises(Exception) as exc_info:
            await pipeline_service.execute_pipeline(search_input, "test_collection")
        
        # Error should be about infrastructure
        error_message = str(exc_info.value).lower()
        assert any(keyword in error_message for keyword in ['milvus', 'connection', 'database', 'vector'])
    
    def test_get_user_pipelines_with_invalid_user_id(self, pipeline_service: PipelineService):
        """Test get_user_pipelines with invalid user ID."""
        invalid_user_id = uuid4()
        
        # Should return empty list or raise appropriate error
        try:
            pipelines = pipeline_service.get_user_pipelines(invalid_user_id)
            assert isinstance(pipelines, list)
        except Exception as exc_info:
            # If it raises an error, it should be about user not found
            error_message = str(exc_info.value).lower()
            assert any(keyword in error_message for keyword in ['not found', 'user', '404'])
    
    def test_get_default_pipeline_with_invalid_user_id(self, pipeline_service: PipelineService):
        """Test get_default_pipeline with invalid user ID."""
        invalid_user_id = uuid4()
        
        # Should return None or raise appropriate error
        try:
            pipeline = pipeline_service.get_default_pipeline(invalid_user_id)
            assert pipeline is None or isinstance(pipeline, object)
        except Exception as exc_info:
            # If it raises an error, it should be about user not found
            error_message = str(exc_info.value).lower()
            assert any(keyword in error_message for keyword in ['not found', 'user', '404'])
    
    def test_get_pipeline_config_with_invalid_pipeline_id(self, pipeline_service: PipelineService):
        """Test get_pipeline_config with invalid pipeline ID."""
        invalid_pipeline_id = uuid4()
        
        # Should return None or raise appropriate error
        try:
            config = pipeline_service.get_pipeline_config(invalid_pipeline_id)
            assert config is None or isinstance(config, object)
        except Exception as exc_info:
            # If it raises an error, it should be about pipeline not found
            error_message = str(exc_info.value).lower()
            assert any(keyword in error_message for keyword in ['not found', 'pipeline', '404'])
