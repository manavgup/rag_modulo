"""Tests for pipeline service with different LLM providers."""
import pytest
from typing import Dict, Any, List
from uuid import UUID

from rag_solution.services.pipeline_service import PipelineService
from rag_solution.services.llm_provider_service import LLMProviderService
from rag_solution.services.llm_parameters_service import LLMParametersService
from rag_solution.schemas.llm_provider_schema import ModelType
from rag_solution.services.prompt_template_service import PromptTemplateService
from rag_solution.services.user_service import UserService
from rag_solution.schemas.user_schema import UserInput
from rag_solution.schemas.prompt_template_schema import PromptTemplateType
from rag_solution.generation.providers.watsonx import WatsonXLLM
from rag_solution.generation.providers.openai import OpenAILLM
from rag_solution.generation.providers.anthropic import AnthropicLLM

@pytest.mark.provider
class TestPipelineProviders:
    """Test pipeline service with different LLM providers."""

    @pytest.fixture
    def test_user(self, db_session):
        """Create test user."""
        user_service = UserService(db_session)
        user = user_service.create_user(UserInput(
            ibm_id="test_ibm_id",
            email="test@example.com",
            name="Test User"
        ))
        return user

    @pytest.fixture
    def pipeline_service(self, db_session) -> PipelineService:
        """Create pipeline service fixture."""
        return PipelineService(db_session)

    @pytest.fixture
    def provider_data(self) -> Dict[str, Dict[str, Any]]:
        """Test provider data."""
        return {
            "watsonx": {
                "name": "test-watsonx",
                "base_url": "https://test.watsonx.ai/api",
                "api_key": "test-key",
                "project_id": "test-project",
                "is_active": True,
                "models": [
                    {
                        "model_id": "granite-13b",
                        "model_type": ModelType.GENERATION,
                        "is_default": True,
                        "max_tokens": 2048
                    },
                    {
                        "model_id": "embedding-model",
                        "model_type": ModelType.EMBEDDING,
                        "is_default": True,
                        "max_tokens": 512
                    }
                ]
            },
            "openai": {
                "name": "test-openai",
                "base_url": "https://api.openai.com/v1",
                "api_key": "test-key",
                "is_active": True,
                "models": [
                    {
                        "model_id": "gpt-4",
                        "model_type": ModelType.GENERATION,
                        "is_default": True,
                        "max_tokens": 8192
                    },
                    {
                        "model_id": "text-embedding-ada-002",
                        "model_type": ModelType.EMBEDDING,
                        "is_default": True,
                        "max_tokens": 8191
                    }
                ]
            },
            "anthropic": {
                "name": "test-anthropic",
                "base_url": "https://api.anthropic.com",
                "api_key": "test-key",
                "is_active": True,
                "models": [
                    {
                        "model_id": "claude-2",
                        "model_type": ModelType.GENERATION,
                        "is_default": True,
                        "max_tokens": 100000
                    }
                ]
            }
        }

    @pytest.fixture
    def llm_parameters(self, test_user) -> Dict[str, Dict[str, Any]]:
        """Test LLM parameters for each provider."""
        return {
            "watsonx": {
                "name": "watsonx-params",
                "user_id": test_user.id,
                "provider": "watsonx",
                "model_id": "granite-13b",
                "temperature": 0.7,
                "max_new_tokens": 1000,
                "is_default": True
            },
            "openai": {
                "name": "openai-params",
                "user_id": test_user.id,
                "provider": "openai",
                "model_id": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 1000,
                "is_default": True
            },
            "anthropic": {
                "name": "anthropic-params",
                "user_id": test_user.id,
                "provider": "anthropic",
                "model_id": "claude-2",
                "temperature": 0.7,
                "max_tokens": 1000,
                "is_default": True
            }
        }

    @pytest.fixture
    def prompt_templates(self, test_user) -> Dict[str, Dict[str, Any]]:
        """Test prompt templates for each provider."""
        return {
            "watsonx": {
                "name": "watsonx-template",
                "user_id": test_user.id,
                "provider": "watsonx",
                "template_type": PromptTemplateType.RAG_QUERY,
                "template_format": "Context:\n{context}\nQuestion:{question}",
                "is_default": True
            },
            "openai": {
                "name": "openai-template",
                "user_id": test_user.id,
                "provider": "openai",
                "template_type": PromptTemplateType.RAG_QUERY,
                "template_format": "Context:\n{context}\nQuestion:{question}",
                "is_default": True
            },
            "anthropic": {
                "name": "anthropic-template",
                "user_id": test_user.id,
                "provider": "anthropic",
                "template_type": PromptTemplateType.RAG_QUERY,
                "template_format": "Context:\n{context}\nQuestion:{question}",
                "is_default": True
            }
        }

    @pytest.fixture
    def test_documents(self) -> List[Dict[str, Any]]:
        """Test documents for retrieval."""
        return [
            {
                "content": "Python is a high-level programming language.",
                "metadata": {"source": "test.txt"}
            },
            {
                "content": "Python was created by Guido van Rossum.",
                "metadata": {"source": "test.txt"}
            }
        ]

    @pytest.mark.integration
    async def test_watsonx_pipeline(
        self,
        pipeline_service: PipelineService,
        provider_data: Dict[str, Dict[str, Any]],
        llm_parameters: Dict[str, Dict[str, Any]],
        prompt_templates: Dict[str, Dict[str, Any]],
        test_documents: List[Dict[str, Any]],
        test_user,
        db_session
    ):
        """Test pipeline with WatsonX provider."""
        # Create provider with models
        llm_provider_service = LLMProviderService(db_session)
        provider = llm_provider_service.create_provider(provider_data["watsonx"])
        gen_model = next(
            m for m in llm_provider_service.get_models_by_provider(provider.id)
            if m.model_type == ModelType.GENERATION
        )

        # Initialize pipeline with WatsonX
        await pipeline_service.initialize(
            provider_id=provider.id,
            model_id=gen_model.model_id,
            llm_parameters=llm_parameters["watsonx"],
            prompt_template=prompt_templates["watsonx"],
            user_id=test_user.id
        )

        # Execute pipeline
        result = await pipeline_service.execute_pipeline(
            question="Who created Python?",
            documents=test_documents,
            user_id=test_user.id
        )

        # Verify WatsonX-specific results
        assert isinstance(pipeline_service.provider, WatsonXLLM)
        assert "Guido van Rossum" in result.generated_answer
        assert result.provider_name == "watsonx"

    @pytest.mark.integration
    async def test_openai_pipeline(
        self,
        pipeline_service: PipelineService,
        provider_data: Dict[str, Dict[str, Any]],
        llm_parameters: Dict[str, Dict[str, Any]],
        prompt_templates: Dict[str, Dict[str, Any]],
        test_documents: List[Dict[str, Any]],
        test_user,
        db_session
    ):
        """Test pipeline with OpenAI provider."""
        # Create provider with models
        llm_provider_service = LLMProviderService(db_session)
        provider = llm_provider_service.create_provider(provider_data["openai"])
        gen_model = next(
            m for m in llm_provider_service.get_models_by_provider(provider.id)
            if m.model_type == ModelType.GENERATION
        )

        # Initialize pipeline with OpenAI
        await pipeline_service.initialize(
            provider_id=provider.id,
            model_id=gen_model.model_id,
            llm_parameters=llm_parameters["openai"],
            prompt_template=prompt_templates["openai"],
            user_id=test_user.id
        )

        # Execute pipeline
        result = await pipeline_service.execute_pipeline(
            question="Who created Python?",
            documents=test_documents,
            user_id=test_user.id
        )

        # Verify OpenAI-specific results
        assert isinstance(pipeline_service.provider, OpenAILLM)
        assert "Guido van Rossum" in result.generated_answer
        assert result.provider_name == "openai"

    @pytest.mark.integration
    async def test_anthropic_pipeline(
        self,
        pipeline_service: PipelineService,
        provider_data: Dict[str, Dict[str, Any]],
        llm_parameters: Dict[str, Dict[str, Any]],
        prompt_templates: Dict[str, Dict[str, Any]],
        test_documents: List[Dict[str, Any]],
        test_user,
        db_session
    ):
        """Test pipeline with Anthropic provider."""
        # Create provider with models
        llm_provider_service = LLMProviderService(db_session)
        provider = llm_provider_service.create_provider(provider_data["anthropic"])
        gen_model = next(
            m for m in llm_provider_service.get_models_by_provider(provider.id)
            if m.model_type == ModelType.GENERATION
        )

        # Initialize pipeline with Anthropic
        await pipeline_service.initialize(
            provider_id=provider.id,
            model_id=gen_model.model_id,
            llm_parameters=llm_parameters["anthropic"],
            prompt_template=prompt_templates["anthropic"],
            user_id=test_user.id
        )

        # Execute pipeline
        result = await pipeline_service.execute_pipeline(
            question="Who created Python?",
            documents=test_documents,
            user_id=test_user.id
        )

        # Verify Anthropic-specific results
        assert isinstance(pipeline_service.provider, AnthropicLLM)
        assert "Guido van Rossum" in result.generated_answer
        assert result.provider_name == "anthropic"

    @pytest.mark.integration
    async def test_multiple_users_providers(
        self,
        pipeline_service: PipelineService,
        provider_data: Dict[str, Dict[str, Any]],
        llm_parameters: Dict[str, Dict[str, Any]],
        prompt_templates: Dict[str, Dict[str, Any]],
        test_documents: List[Dict[str, Any]],
        test_user,
        db_session
    ):
        """Test pipeline with different providers for different users."""
        # Create second user
        user_service = UserService(db_session)
        user2 = user_service.create_user(UserInput(
            ibm_id="test_ibm_id_2",
            email="test2@example.com",
            name="Test User 2"
        ))

        # Create providers with models
        llm_provider_service = LLMProviderService(db_session)
        
        # WatsonX for first user
        watsonx_provider = llm_provider_service.create_provider(provider_data["watsonx"])
        watsonx_model = next(
            m for m in llm_provider_service.get_models_by_provider(watsonx_provider.id)
            if m.model_type == ModelType.GENERATION
        )

        # OpenAI for second user
        openai_provider = llm_provider_service.create_provider(provider_data["openai"])
        openai_model = next(
            m for m in llm_provider_service.get_models_by_provider(openai_provider.id)
            if m.model_type == ModelType.GENERATION
        )

        # Initialize pipeline with WatsonX for first user
        await pipeline_service.initialize(
            provider_id=watsonx_provider.id,
            model_id=watsonx_model.model_id,
            llm_parameters={
                **llm_parameters["watsonx"],
                "user_id": test_user.id
            },
            prompt_template={
                **prompt_templates["watsonx"],
                "user_id": test_user.id
            },
            user_id=test_user.id
        )

        # Initialize pipeline with OpenAI for second user
        await pipeline_service.initialize(
            provider_id=openai_provider.id,
            model_id=openai_model.model_id,
            llm_parameters={
                **llm_parameters["openai"],
                "user_id": user2.id
            },
            prompt_template={
                **prompt_templates["openai"],
                "user_id": user2.id
            },
            user_id=user2.id
        )

        # Execute pipeline for first user
        result1 = await pipeline_service.execute_pipeline(
            question="Who created Python?",
            documents=test_documents,
            user_id=test_user.id
        )

        # Execute pipeline for second user
        result2 = await pipeline_service.execute_pipeline(
            question="Who created Python?",
            documents=test_documents,
            user_id=user2.id
        )

        # Verify user-specific results
        assert result1.provider_name == "watsonx"
        assert result2.provider_name == "openai"
        assert "Guido van Rossum" in result1.generated_answer
        assert "Guido van Rossum" in result2.generated_answer

    @pytest.mark.performance
    async def test_provider_performance(
        self,
        pipeline_service: PipelineService,
        provider_data: Dict[str, Dict[str, Any]],
        llm_parameters: Dict[str, Dict[str, Any]],
        prompt_templates: Dict[str, Dict[str, Any]],
        test_documents: List[Dict[str, Any]],
        test_user,
        db_session
    ):
        """Test performance across different providers."""
        import time
        import asyncio

        llm_provider_service = LLMProviderService(db_session)
        results = {}

        for provider_name in ["watsonx", "openai", "anthropic"]:
            # Create provider with models
            provider = llm_provider_service.create_provider(provider_data[provider_name])
            gen_model = next(
                m for m in llm_provider_service.get_models_by_provider(provider.id)
                if m.model_type == ModelType.GENERATION
            )

            # Initialize pipeline with provider
            await pipeline_service.initialize(
                provider_id=provider.id,
                model_id=gen_model.model_id,
                llm_parameters=llm_parameters[provider_name],
                prompt_template=prompt_templates[provider_name],
                user_id=test_user.id
            )

            # Measure performance
            start_time = time.time()
            result = await pipeline_service.execute_pipeline(
                question="Who created Python?",
                documents=test_documents,
                user_id=test_user.id
            )
            end_time = time.time()

            results[provider] = {
                "execution_time": end_time - start_time,
                "token_count": len(result.generated_answer.split()),
                "success": "Guido van Rossum" in result.generated_answer
            }

        # Verify performance metrics
        for provider, metrics in results.items():
            assert metrics["execution_time"] < 5.0  # Should complete within 5 seconds
            assert metrics["token_count"] > 0
            assert metrics["success"]

    @pytest.mark.error
    async def test_provider_error_handling(
        self,
        pipeline_service: PipelineService,
        provider_data: Dict[str, Dict[str, Any]],
        llm_parameters: Dict[str, Dict[str, Any]],
        prompt_templates: Dict[str, Dict[str, Any]],
        test_user,
        db_session
    ):
        """Test error handling for different providers."""
        llm_provider_service = LLMProviderService(db_session)

        for provider_name in ["watsonx", "openai", "anthropic"]:
            # Test with invalid API key
            invalid_data = {
                **provider_data[provider_name],
                "api_key": "invalid-key"
            }
            provider = llm_provider_service.create_provider(invalid_data)
            gen_model = next(
                m for m in llm_provider_service.get_models_by_provider(provider.id)
                if m.model_type == ModelType.GENERATION
            )

            with pytest.raises(Exception) as exc:
                await pipeline_service.initialize(
                    provider_id=provider.id,
                    model_id=gen_model.model_id,
                    llm_parameters=llm_parameters[provider_name],
                    prompt_template=prompt_templates[provider_name],
                    user_id=test_user.id
                )
                assert "authentication failed" in str(exc.value).lower()

            # Test with invalid model ID
            invalid_params = {
                **llm_parameters[provider],
                "model_id": "invalid-model"
            }

            with pytest.raises(Exception) as exc:
                await pipeline_service.initialize(
                    provider_config=provider_configs[provider],
                    llm_parameters=invalid_params,
                    prompt_template=prompt_templates[provider],
                    user_id=test_user.id
                )
                assert "model not found" in str(exc.value).lower()

    @pytest.mark.error
    async def test_user_specific_error_handling(
        self,
        pipeline_service: PipelineService,
        provider_configs: Dict[str, Dict[str, Any]],
        llm_parameters: Dict[str, Dict[str, Any]],
        prompt_templates: Dict[str, Dict[str, Any]],
        test_user
    ):
        """Test user-specific error handling."""
        # Test with non-existent user
        with pytest.raises(Exception) as exc:
            await pipeline_service.initialize(
                provider_config=provider_configs["watsonx"],
                llm_parameters=llm_parameters["watsonx"],
                prompt_template=prompt_templates["watsonx"],
                user_id=UUID("00000000-0000-0000-0000-000000000000")
            )
            assert "user not found" in str(exc.value).lower()

        # Test with missing user_id in parameters
        invalid_params = {
            **llm_parameters["watsonx"]
        }
        del invalid_params["user_id"]

        with pytest.raises(Exception) as exc:
            await pipeline_service.initialize(
                provider_config=provider_configs["watsonx"],
                llm_parameters=invalid_params,
                prompt_template=prompt_templates["watsonx"],
                user_id=test_user.id
            )
            assert "user_id is required" in str(exc.value).lower()
