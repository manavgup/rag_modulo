import logging
import pytest
from uuid import uuid4
from datetime import datetime
from rag_solution.models.prompt_template import PromptTemplate
from rag_solution.schemas.prompt_template_schema import (
    PromptTemplateCreate,
    PromptTemplateUpdate,
    PromptTemplateResponse
)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# -------------------------------------------
# 🧪 TEST TEMPLATE CREATION
# -------------------------------------------
def test_create_template():
    """Test creating a prompt template with variable substitution."""
    logger.info("Starting test_create_template")
    template = PromptTemplate(
        id=str(uuid4()),
        name="test_template",
        provider="watsonx",
        system_prompt="You are a helpful AI assistant.",
        context_prefix="Context:\n",
        query_prefix="Question:\n",
        answer_prefix="Answer:\n",
        input_variables=["topic", "aspect"],
        template_format="Explain {topic}, focusing on {aspect}."
    )
    
    formatted = template.format_prompt(
        topic="quantum computing",
        aspect="practical applications"
    )
    expected = (
        "You are a helpful AI assistant.\n"
        "Context:\n"
        "Explain quantum computing, focusing on practical applications.\n"
        "Question:\n"
    )
    assert formatted == expected

    # Test missing variable
    with pytest.raises(ValueError, match="Missing required variables"):
        template.format_prompt(topic="quantum computing")
    
    # Test undeclared variable
    with pytest.raises(ValueError, match="Received undeclared variables"):
        template.format_prompt(
            topic="quantum computing",
            aspect="applications",
            extra="invalid"
        )


# -------------------------------------------
# 🧪 TEST TEMPLATE VALIDATION
# -------------------------------------------
def test_template_validation():
    """Test template validation."""
    logger.info("Starting test_template_validation")
    template = PromptTemplate(
        id=str(uuid4()),
        name="valid_template",
        provider="watsonx",
        system_prompt="You are a helpful AI assistant.",
        context_prefix="Context:\n",
        query_prefix="Question:\n",
        answer_prefix="Answer:\n",
        input_variables=["topic"],
        template_format="What is {topic}?"
    )
    assert template.input_variables == ["topic"]
    
    # Test invalid variables in template
    with pytest.raises(ValueError, match="Template contains undeclared variables"):
        PromptTemplate(
            id=str(uuid4()),
            name="invalid_template",
            provider="watsonx",
            system_prompt="You are a helpful AI assistant.",
            context_prefix="Context:\n",
            query_prefix="Question:\n",
            answer_prefix="Answer:\n",
            input_variables=["topic"],
            template_format="What is {topic} and {undefined_var}?"
        )


# -------------------------------------------
# 🧪 TEST LLaMA3-SPECIFIC TEMPLATE
# -------------------------------------------
def test_llama3_template_format():
    """Test proper formatting for LLaMA3 templates."""
    logger.info("Starting test_llama3_template_format")
    template = PromptTemplate(
        id=str(uuid4()),
        name="llama3_template",
        provider="llama3",
        system_prompt="",  # Empty system prompt for LLaMA
        context_prefix="",  # No context prefix needed
        query_prefix="",   # No query prefix needed
        answer_prefix="",  # No answer prefix needed
        input_variables=["instruction", "context"],
        template_format="[INST] {instruction}\nContext: {context} [/INST]"
    )
    
    formatted = template.format_prompt(
        instruction="Explain machine learning",
        context="Focus on supervised learning"
    ).strip()
    
    expected = "[INST] Explain machine learning\nContext: Focus on supervised learning [/INST]"
    assert formatted == expected

    # Validate missing variables
    with pytest.raises(ValueError, match="Missing required variables"):
        template.format_prompt(instruction="Explain AI")

    # Validate extra variables
    with pytest.raises(ValueError, match="Received undeclared variables"):
        template.format_prompt(
            instruction="Explain AI",
            context="Focus on ethics",
            extra_var="invalid"
        )



# -------------------------------------------
# 🧪 TEST EMPTY TEMPLATE HANDLING
# -------------------------------------------
def test_template_with_empty_fields():
    """Test handling of templates with empty fields."""
    logger.info("Starting test_template_with_empty_fields")
    template = PromptTemplate(
        id=str(uuid4()),
        name="empty_template",
        provider="watsonx",
        system_prompt="",
        context_prefix="",
        query_prefix="",
        answer_prefix="",
        input_variables=[],
        template_format=""
    )
    
    assert template.system_prompt == ""
    assert template.context_prefix == ""
    assert template.input_variables == []
    
    # Test that empty template falls back to using question directly
    formatted = template.format_prompt(question="What is AI?")
    assert formatted == "What is AI?"
    
    # Test that missing question raises error when no template format
    with pytest.raises(ValueError, match="No question provided and no template format defined"):
        template.format_prompt()


# -------------------------------------------
# 🧪 TEST INVALID PROVIDER
# -------------------------------------------
def test_invalid_provider():
    """Test validation of provider field."""
    logger.info("Starting test_invalid_provider")
    with pytest.raises(ValueError, match="Invalid provider"):
        PromptTemplateCreate(
            name="invalid_provider_template",
            provider="unsupported_provider",
            template_format="Some format"
        )


# -------------------------------------------
# 🧪 TEST PROMPT TEMPLATE SCHEMA
# -------------------------------------------
def test_example_templates():
    """Test example templates for different providers."""
    logger.info("Starting test_example_templates")
    
    # Test watsonx example template
    watsonx_template = PromptTemplate.get_example_template("watsonx")
    assert watsonx_template is not None
    assert watsonx_template["provider"] == "watsonx"
    assert "system_prompt" in watsonx_template
    assert "input_variables" in watsonx_template
    
    # Test llama2 example template
    llama2_template = PromptTemplate.get_example_template("llama2")
    assert llama2_template is not None
    assert llama2_template["provider"] == "llama2"
    assert "[INST]" in llama2_template["system_prompt"]
    
    # Test non-existent provider
    assert PromptTemplate.get_example_template("nonexistent") is None

def test_prompt_template_schema():
    """Test schema validation for prompt template."""
    logger.info("Starting test_prompt_template_schema")
    data = {
        "name": "schema_template",
        "provider": "watsonx",
        "system_prompt": "Test system prompt",
        "context_prefix": "Context:\n",
        "query_prefix": "User:\n",
        "answer_prefix": "Assistant:\n",
        "input_variables": ["topic"],
        "template_format": "Explain {topic}"
    }
    
    template = PromptTemplateCreate(**data)
    assert template.name == "schema_template"
    assert template.input_variables == ["topic"]

    # Invalid variable in schema
    data["template_format"] = "Explain {unknown}"
    with pytest.raises(ValueError, match="Template contains undeclared variables"):
        PromptTemplateCreate(**data)


# -------------------------------------------
# 🧪 TEST TO_DICT METHOD
# -------------------------------------------
def test_to_dict():
    """Test conversion of template to dictionary."""
    logger.info("Starting test_to_dict")
    template_id = str(uuid4())
    template = PromptTemplate(
        id=template_id,
        name="test_template",
        provider="watsonx",
        system_prompt="Test prompt",
        context_prefix="Context:\n",
        query_prefix="Question:\n",
        answer_prefix="Answer:\n",
        input_variables=["topic"],
        template_format="What is {topic}?"
    )
    
    dict_data = template.to_dict()
    assert dict_data["id"] == template_id
    assert dict_data["input_variables"] == ["topic"]
    assert dict_data["template_format"] == "What is {topic}?"
