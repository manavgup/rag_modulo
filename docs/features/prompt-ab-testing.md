# Prompt A/B Testing Framework

## Overview

A/B testing framework for comparing different prompt formats to optimize Chain of Thought (CoT) response quality.

---

## Architecture

### Components

```
User Request
    ↓
Experiment Manager (assigns variant)
    ↓
Prompt Factory (generates prompt based on variant)
    ↓
LLM Service
    ↓
Response Parser
    ↓
Metrics Tracker (records success/quality)
    ↓
Analytics Dashboard
```

---

## Implementation Plan

### 1. Prompt Variants Schema

**File**: `backend/rag_solution/schemas/prompt_variant_schema.py`

```python
"""Prompt variant schemas for A/B testing."""

from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class PromptFormat(str, Enum):
    """Supported prompt formats."""

    XML_TAGS = "xml_tags"  # <thinking>...<answer>
    JSON_STRUCTURE = "json_structure"  # {"reasoning": "...", "answer": "..."}
    MARKDOWN_HEADERS = "markdown_headers"  # ## Reasoning\n## Answer
    FINAL_ANSWER_MARKER = "final_answer_marker"  # Reasoning: ...\nFinal Answer: ...
    CUSTOM = "custom"  # User-defined format


class PromptVariant(BaseModel):
    """A/B test prompt variant."""

    id: UUID
    name: str = Field(..., description="Variant name (e.g., 'xml-with-examples')")
    format: PromptFormat
    system_instructions: str
    few_shot_examples: list[str] = Field(default_factory=list)
    template: str
    is_active: bool = True
    weight: float = Field(1.0, ge=0.0, le=1.0, description="Traffic allocation weight")

    class Config:
        """Pydantic config."""

        use_enum_values = True


class ExperimentConfig(BaseModel):
    """A/B test experiment configuration."""

    id: UUID
    name: str = Field(..., description="Experiment name")
    description: str | None = None
    variants: list[PromptVariant]
    control_variant_id: UUID  # Which variant is the control
    traffic_allocation: dict[str, float]  # variant_id -> percentage (0.0-1.0)
    is_active: bool = True
    start_date: str | None = None
    end_date: str | None = None

    class Config:
        """Pydantic config."""

        use_enum_values = True


class ExperimentMetrics(BaseModel):
    """Metrics for an experiment variant."""

    variant_id: UUID
    total_requests: int = 0
    successful_parses: int = 0
    parse_success_rate: float = 0.0
    avg_quality_score: float = 0.0
    avg_response_time_ms: float = 0.0
    retry_rate: float = 0.0
    artifact_rate: float = 0.0  # % of responses with artifacts
```

---

### 2. Experiment Manager Service

**File**: `backend/rag_solution/services/experiment_manager_service.py`

```python
"""A/B testing experiment manager."""

import hashlib
import logging
from uuid import UUID

from sqlalchemy.orm import Session

from core.config import Settings
from rag_solution.schemas.prompt_variant_schema import (
    ExperimentConfig,
    PromptVariant,
)

logger = logging.getLogger(__name__)


class ExperimentManagerService:
    """Manage A/B testing experiments for prompt optimization."""

    def __init__(self, db: Session, settings: Settings):
        """Initialize experiment manager.

        Args:
            db: Database session
            settings: Application settings
        """
        self.db = db
        self.settings = settings
        self._experiments_cache: dict[str, ExperimentConfig] = {}

    def get_variant_for_user(
        self,
        experiment_name: str,
        user_id: str
    ) -> PromptVariant:
        """Assign a variant to a user using consistent hashing.

        Args:
            experiment_name: Name of the experiment
            user_id: User identifier

        Returns:
            Assigned prompt variant
        """
        # Get experiment config
        experiment = self._get_experiment(experiment_name)

        if not experiment or not experiment.is_active:
            # Return control variant if experiment not active
            return self._get_control_variant(experiment_name)

        # Use consistent hashing to assign variant
        variant_id = self._hash_user_to_variant(
            user_id,
            experiment.traffic_allocation
        )

        # Find variant
        variant = next(
            (v for v in experiment.variants if str(v.id) == variant_id),
            None
        )

        if not variant:
            logger.warning(
                "Variant %s not found for experiment %s, using control",
                variant_id,
                experiment_name
            )
            return self._get_control_variant(experiment_name)

        logger.debug(
            "Assigned user %s to variant %s in experiment %s",
            user_id,
            variant.name,
            experiment_name
        )

        return variant

    def _hash_user_to_variant(
        self,
        user_id: str,
        traffic_allocation: dict[str, float]
    ) -> str:
        """Hash user ID to variant ID using consistent hashing.

        Args:
            user_id: User identifier
            traffic_allocation: Variant ID -> traffic percentage

        Returns:
            Selected variant ID
        """
        # Create deterministic hash from user_id
        hash_value = int(hashlib.sha256(user_id.encode()).hexdigest(), 16)
        bucket = (hash_value % 100) / 100.0  # 0.00 to 0.99

        # Assign to variant based on traffic allocation
        cumulative = 0.0
        for variant_id, percentage in sorted(traffic_allocation.items()):
            cumulative += percentage
            if bucket < cumulative:
                return variant_id

        # Fallback to first variant
        return list(traffic_allocation.keys())[0]

    def _get_experiment(self, experiment_name: str) -> ExperimentConfig | None:
        """Get experiment configuration.

        Args:
            experiment_name: Name of the experiment

        Returns:
            Experiment config or None
        """
        # Check cache first
        if experiment_name in self._experiments_cache:
            return self._experiments_cache[experiment_name]

        # In production, load from database
        # For now, return hardcoded experiments
        experiments = self._get_default_experiments()

        experiment = experiments.get(experiment_name)
        if experiment:
            self._experiments_cache[experiment_name] = experiment

        return experiment

    def _get_control_variant(self, experiment_name: str) -> PromptVariant:
        """Get control variant for experiment.

        Args:
            experiment_name: Name of the experiment

        Returns:
            Control variant
        """
        experiment = self._get_experiment(experiment_name)
        if not experiment:
            # Return default XML variant
            return self._get_default_xml_variant()

        control = next(
            (v for v in experiment.variants if v.id == experiment.control_variant_id),
            None
        )

        return control or self._get_default_xml_variant()

    def _get_default_xml_variant(self) -> PromptVariant:
        """Get default XML variant (our current implementation).

        Returns:
            Default variant
        """
        from uuid import uuid4
        from rag_solution.schemas.prompt_variant_schema import PromptFormat

        return PromptVariant(
            id=uuid4(),
            name="xml-tags-control",
            format=PromptFormat.XML_TAGS,
            system_instructions="Use <thinking> and <answer> tags",
            few_shot_examples=[],
            template="<thinking>{reasoning}</thinking><answer>{answer}</answer>",
            is_active=True,
            weight=1.0
        )

    def _get_default_experiments(self) -> dict[str, ExperimentConfig]:
        """Get default experiment configurations.

        Returns:
            Dictionary of experiment name -> config
        """
        from uuid import uuid4
        from rag_solution.schemas.prompt_variant_schema import PromptFormat

        # Example: Test XML vs JSON vs Markdown
        variant_xml = PromptVariant(
            id=uuid4(),
            name="xml-tags",
            format=PromptFormat.XML_TAGS,
            system_instructions=(
                "You are a RAG assistant. Use XML tags for your response.\n"
                "Put reasoning in <thinking> tags.\n"
                "Put final answer in <answer> tags."
            ),
            few_shot_examples=[
                "Question: What is 2+2?\n"
                "<thinking>2 plus 2 equals 4</thinking>\n"
                "<answer>4</answer>"
            ],
            template="<thinking>{reasoning}</thinking><answer>{answer}</answer>",
            is_active=True,
            weight=1.0
        )

        variant_json = PromptVariant(
            id=uuid4(),
            name="json-structure",
            format=PromptFormat.JSON_STRUCTURE,
            system_instructions=(
                "You are a RAG assistant. Return your response as JSON.\n"
                'Format: {"reasoning": "...", "answer": "..."}'
            ),
            few_shot_examples=[
                'Question: What is 2+2?\n'
                '{"reasoning": "2 plus 2 equals 4", "answer": "4"}'
            ],
            template='{"reasoning": "{reasoning}", "answer": "{answer}"}',
            is_active=True,
            weight=1.0
        )

        variant_markdown = PromptVariant(
            id=uuid4(),
            name="markdown-headers",
            format=PromptFormat.MARKDOWN_HEADERS,
            system_instructions=(
                "You are a RAG assistant. Use markdown headers for your response.\n"
                "Use ## Reasoning for your thinking.\n"
                "Use ## Answer for the final answer."
            ),
            few_shot_examples=[
                "Question: What is 2+2?\n"
                "## Reasoning\n2 plus 2 equals 4\n"
                "## Answer\n4"
            ],
            template="## Reasoning\n{reasoning}\n## Answer\n{answer}",
            is_active=True,
            weight=1.0
        )

        experiment = ExperimentConfig(
            id=uuid4(),
            name="prompt-format-test",
            description="Test XML vs JSON vs Markdown prompt formats",
            variants=[variant_xml, variant_json, variant_markdown],
            control_variant_id=variant_xml.id,
            traffic_allocation={
                str(variant_xml.id): 0.34,  # 34% XML (control)
                str(variant_json.id): 0.33,  # 33% JSON
                str(variant_markdown.id): 0.33,  # 33% Markdown
            },
            is_active=True,
        )

        return {"prompt-format-test": experiment}
```

---

### 3. Prompt Factory with Variant Support

**File**: Update `backend/rag_solution/services/chain_of_thought_service.py`

```python
def _create_prompt_with_variant(
    self,
    question: str,
    context: list[str],
    variant: PromptVariant
) -> str:
    """Create prompt using specified variant.

    Args:
        question: User question
        context: Context passages
        variant: Prompt variant to use

    Returns:
        Formatted prompt
    """
    from rag_solution.schemas.prompt_variant_schema import PromptFormat

    # Format context
    context_str = " ".join(context)

    # Build prompt based on variant format
    if variant.format == PromptFormat.XML_TAGS:
        return self._create_xml_prompt(
            question, context_str, variant
        )
    elif variant.format == PromptFormat.JSON_STRUCTURE:
        return self._create_json_prompt(
            question, context_str, variant
        )
    elif variant.format == PromptFormat.MARKDOWN_HEADERS:
        return self._create_markdown_prompt(
            question, context_str, variant
        )
    elif variant.format == PromptFormat.FINAL_ANSWER_MARKER:
        return self._create_marker_prompt(
            question, context_str, variant
        )
    else:
        # Fallback to XML
        return self._create_enhanced_prompt(question, context)

def _create_xml_prompt(
    self, question: str, context_str: str, variant: PromptVariant
) -> str:
    """Create XML-formatted prompt."""
    examples = "\n\n".join(variant.few_shot_examples) if variant.few_shot_examples else ""

    return f"""{variant.system_instructions}

{examples}

Question: {question}
Context: {context_str}

<thinking>
[Your reasoning here]
</thinking>

<answer>
[Your final answer here]
</answer>"""

def _create_json_prompt(
    self, question: str, context_str: str, variant: PromptVariant
) -> str:
    """Create JSON-formatted prompt."""
    examples = "\n\n".join(variant.few_shot_examples) if variant.few_shot_examples else ""

    return f"""{variant.system_instructions}

{examples}

Question: {question}
Context: {context_str}

Return your response as JSON:
{{"reasoning": "your step-by-step thinking", "answer": "your final answer"}}"""

def _create_markdown_prompt(
    self, question: str, context_str: str, variant: PromptVariant
) -> str:
    """Create Markdown-formatted prompt."""
    examples = "\n\n".join(variant.few_shot_examples) if variant.few_shot_examples else ""

    return f"""{variant.system_instructions}

{examples}

Question: {question}
Context: {context_str}

## Reasoning
[Your step-by-step thinking here]

## Answer
[Your final answer here]"""
```

---

### 4. Metrics Tracking Service

**File**: `backend/rag_solution/services/experiment_metrics_service.py`

```python
"""Track A/B testing metrics."""

import logging
import time
from uuid import UUID

from sqlalchemy.orm import Session

from core.config import Settings

logger = logging.getLogger(__name__)


class ExperimentMetricsService:
    """Track metrics for A/B testing experiments."""

    def __init__(self, db: Session, settings: Settings):
        """Initialize metrics service.

        Args:
            db: Database session
            settings: Application settings
        """
        self.db = db
        self.settings = settings

    def track_response(
        self,
        experiment_name: str,
        variant_id: str,
        user_id: str,
        question: str,
        raw_response: str,
        parsed_response: str,
        quality_score: float,
        response_time_ms: float,
        parse_success: bool,
        retry_count: int,
        contains_artifacts: bool,
    ) -> None:
        """Track a response for A/B testing.

        Args:
            experiment_name: Name of the experiment
            variant_id: Variant ID used
            user_id: User ID
            question: User question
            raw_response: Raw LLM response
            parsed_response: Parsed clean answer
            quality_score: Quality score (0.0-1.0)
            response_time_ms: Response time in milliseconds
            parse_success: Whether parsing succeeded
            retry_count: Number of retries needed
            contains_artifacts: Whether response contained artifacts
        """
        # Log to structured logs for analytics
        logger.info(
            "experiment_response",
            extra={
                "experiment_name": experiment_name,
                "variant_id": variant_id,
                "user_id": user_id,
                "question_length": len(question),
                "raw_response_length": len(raw_response),
                "parsed_response_length": len(parsed_response),
                "quality_score": quality_score,
                "response_time_ms": response_time_ms,
                "parse_success": parse_success,
                "retry_count": retry_count,
                "contains_artifacts": contains_artifacts,
                "timestamp": time.time(),
            }
        )

        # In production, also store in database for dashboard
        # self._store_to_database(...)

    def get_variant_metrics(
        self, experiment_name: str, variant_id: str
    ) -> dict:
        """Get metrics for a variant.

        Args:
            experiment_name: Name of the experiment
            variant_id: Variant ID

        Returns:
            Dictionary of metrics
        """
        # In production, query from database
        # For now, return sample data
        return {
            "total_requests": 1000,
            "successful_parses": 950,
            "parse_success_rate": 0.95,
            "avg_quality_score": 0.82,
            "avg_response_time_ms": 2600,
            "retry_rate": 0.25,
            "artifact_rate": 0.05,
        }
```

---

### 5. Integration into CoT Service

**Update**: `backend/rag_solution/services/chain_of_thought_service.py`

```python
def __init__(
    self,
    settings: Settings,
    llm_service: LLMBase,
    search_service: "SearchService",
    db: Session
) -> None:
    """Initialize Chain of Thought service."""
    self.db = db
    self.settings = settings
    self.llm_service = llm_service
    self.search_service = search_service

    # Add experiment services
    self._experiment_manager: ExperimentManagerService | None = None
    self._experiment_metrics: ExperimentMetricsService | None = None

    # ... rest of initialization

@property
def experiment_manager(self) -> ExperimentManagerService:
    """Lazy initialization of experiment manager."""
    if self._experiment_manager is None:
        self._experiment_manager = ExperimentManagerService(self.db, self.settings)
    return self._experiment_manager

@property
def experiment_metrics(self) -> ExperimentMetricsService:
    """Lazy initialization of experiment metrics."""
    if self._experiment_metrics is None:
        self._experiment_metrics = ExperimentMetricsService(self.db, self.settings)
    return self._experiment_metrics

def _generate_llm_response_with_experiment(
    self,
    llm_service: LLMBase,
    question: str,
    context: list[str],
    user_id: str
) -> tuple[str, Any]:
    """Generate LLM response using A/B testing variant.

    Args:
        llm_service: The LLM service
        question: The question
        context: Context passages
        user_id: User ID

    Returns:
        Tuple of (parsed answer, usage)
    """
    import time
    start_time = time.time()

    # Get variant for user
    variant = self.experiment_manager.get_variant_for_user(
        "prompt-format-test",  # experiment name
        user_id
    )

    logger.info("Using variant %s for user %s", variant.name, user_id)

    # Create prompt with variant
    prompt = self._create_prompt_with_variant(question, context, variant)

    # Generate response with retry
    parsed_answer, usage, retry_count = self._generate_with_retry_tracking(
        llm_service, user_id, prompt
    )

    # Assess quality
    quality_score = self._assess_answer_quality(parsed_answer, question)
    contains_artifacts = self._contains_artifacts(parsed_answer)

    # Track metrics
    response_time_ms = (time.time() - start_time) * 1000
    self.experiment_metrics.track_response(
        experiment_name="prompt-format-test",
        variant_id=str(variant.id),
        user_id=user_id,
        question=question,
        raw_response="...",  # truncated for logging
        parsed_response=parsed_answer,
        quality_score=quality_score,
        response_time_ms=response_time_ms,
        parse_success=True,
        retry_count=retry_count,
        contains_artifacts=contains_artifacts,
    )

    return (parsed_answer, usage)
```

---

## Configuration

### Enable/Disable A/B Testing

```python
# In .env
ENABLE_AB_TESTING=true
EXPERIMENT_NAME=prompt-format-test
```

### Define Experiments

```python
# In backend/core/config.py
class Settings(BaseSettings):
    # ... existing settings

    enable_ab_testing: bool = False
    experiment_name: str | None = None
```

---

## Dashboard for Results

### Query Metrics

```python
# Example: Compare variants
variant_a_metrics = metrics_service.get_variant_metrics("prompt-format-test", variant_a_id)
variant_b_metrics = metrics_service.get_variant_metrics("prompt-format-test", variant_b_id)

# Compare success rates
if variant_a_metrics["parse_success_rate"] > variant_b_metrics["parse_success_rate"]:
    winner = "Variant A (XML)"
else:
    winner = "Variant B (JSON)"
```

### Analytics Dashboard (Future)

```sql
-- Query experiment results
SELECT
    variant_id,
    COUNT(*) as total_requests,
    AVG(quality_score) as avg_quality,
    AVG(response_time_ms) as avg_latency,
    SUM(CASE WHEN parse_success THEN 1 ELSE 0 END)::FLOAT / COUNT(*) as success_rate
FROM experiment_responses
WHERE experiment_name = 'prompt-format-test'
  AND created_at >= NOW() - INTERVAL '7 days'
GROUP BY variant_id
ORDER BY avg_quality DESC;
```

---

## Statistical Significance

### Sample Size Calculator

```python
def calculate_required_sample_size(
    baseline_rate: float,
    minimum_detectable_effect: float,
    confidence_level: float = 0.95,
    power: float = 0.80
) -> int:
    """Calculate required sample size for A/B test.

    Args:
        baseline_rate: Current success rate (e.g., 0.60 for 60%)
        minimum_detectable_effect: Minimum improvement to detect (e.g., 0.05 for 5%)
        confidence_level: Statistical confidence (default 95%)
        power: Statistical power (default 80%)

    Returns:
        Required sample size per variant
    """
    import scipy.stats as stats

    # Z-scores for confidence and power
    z_alpha = stats.norm.ppf(1 - (1 - confidence_level) / 2)
    z_beta = stats.norm.ppf(power)

    # Effect size
    p1 = baseline_rate
    p2 = baseline_rate + minimum_detectable_effect
    p_pooled = (p1 + p2) / 2

    # Sample size calculation
    numerator = (z_alpha + z_beta) ** 2 * 2 * p_pooled * (1 - p_pooled)
    denominator = (p2 - p1) ** 2

    return int(numerator / denominator) + 1

# Example: Need 60% -> 65% improvement with 95% confidence
sample_size = calculate_required_sample_size(0.60, 0.05)
# Result: ~1570 samples per variant
```

---

## Best Practices

1. **Run for sufficient time** - At least 1-2 weeks
2. **Sufficient sample size** - 1000+ requests per variant minimum
3. **Monitor early** - Check for major issues daily
4. **Statistical significance** - Use proper hypothesis testing
5. **One variable at a time** - Don't test multiple things simultaneously
6. **Document everything** - Record why you started, what you're testing

---

## Example Experiments to Run

### Experiment 1: Prompt Format

- **Control**: XML tags (current)
- **Variant A**: JSON structure
- **Variant B**: Markdown headers
- **Metric**: Parse success rate

### Experiment 2: Few-Shot Examples

- **Control**: 3 examples (current)
- **Variant A**: 0 examples
- **Variant B**: 5 examples
- **Metric**: Quality score

### Experiment 3: System Instructions

- **Control**: 7 rules (current)
- **Variant A**: 3 core rules only
- **Variant B**: 10 detailed rules
- **Metric**: Artifact rate

---

*Last Updated: October 25, 2025*
