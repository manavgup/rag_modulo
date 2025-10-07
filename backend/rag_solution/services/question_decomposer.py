"""Question decomposer component for Chain of Thought reasoning."""

import re

from core.config import Settings
from rag_solution.generation.providers.base import LLMBase
from rag_solution.schemas.chain_of_thought_schema import DecomposedQuestion, QuestionDecomposition


class QuestionDecomposer:
    """Component for decomposing complex questions."""

    def __init__(self, llm_service: LLMBase | None = None, settings: Settings | None = None) -> None:
        """Initialize question decomposer.

        Args:
            llm_service: Optional LLM service for advanced decomposition.
            settings: Configuration settings.
        """
        self.llm_service = llm_service
        self.settings = settings or Settings()  # type: ignore[call-arg]

    async def decompose(self, question: str, max_depth: int = 3) -> QuestionDecomposition:
        """Decompose a question into sub-questions.

        Args:
            question: The question to decompose.
            max_depth: Maximum decomposition depth.

        Returns:
            List of decomposed sub-questions wrapped in a result object.
        """
        decomposed = []

        # Simple decomposition based on conjunctions and question structure
        parts = re.split(r"\s+and\s+|\s+but\s+|\s+however\s+", question, flags=re.IGNORECASE)

        # For comparison questions, enhance decomposition with more steps
        if len(parts) >= 2 and ("compare" in question.lower() or "contrast" in question.lower()):
            # For "Compare X and Y", generate: [What is X?, What is Y?, How do X and Y differ?]
            enhanced_parts = []
            for part in parts[:2]:  # Take first two parts
                clean_part = part.replace("compare", "").replace("contrast", "").strip()
                if clean_part:
                    enhanced_parts.append(f"What is {clean_part}?")
            enhanced_parts.append(f"How do {parts[0].replace('compare', '').strip()} and {parts[1].strip()} differ?")
            parts = enhanced_parts

        if len(parts) == 1:
            # Check for implicit multi-part structure
            if "how" in question.lower() and ("what" in question.lower() or "why" in question.lower()):
                parts = [
                    question[: question.lower().index("how")].strip(),
                    question[question.lower().index("how") :].strip(),
                ]
            elif "?" in question and question.count("?") > 1:
                parts = question.split("?")[:-1]  # Remove empty last element
                parts = [p.strip() + "?" for p in parts]
            elif "why" in question.lower() or "cause" in question.lower():
                # Decompose causal questions into constituent parts
                if "why does" in question.lower():
                    # Extract the main concept and create sub-questions
                    base_question = question
                    parts = [f"What is {self._extract_main_concept(question)}?", base_question]
                elif "how does" in question.lower():
                    # Similar decomposition for "how does" questions
                    base_question = question
                    parts = [f"What is {self._extract_main_concept(question)}?", base_question]

        # Create decomposed questions
        for i, part in enumerate(parts[:max_depth]):
            if part.strip():
                question_type = self._determine_question_type(part)

                # Calculate complexity score based on type and length
                base_score = min(1.0, len(part.split()) / 50.0)

                # Boost scores for inherently complex question types
                if question_type == "comparison":
                    complexity_score = max(0.6, base_score)
                elif question_type == "causal":
                    complexity_score = max(0.5, base_score)
                elif question_type == "procedural":
                    complexity_score = max(0.4, base_score)
                else:
                    complexity_score = base_score

                decomposed.append(
                    DecomposedQuestion(
                        sub_question=part.strip() if part.strip().endswith("?") else part.strip() + "?",
                        reasoning_step=i + 1,
                        dependency_indices=list(range(i)) if i > 0 else [],
                        question_type=question_type,
                        complexity_score=complexity_score,
                    )
                )

        # If no decomposition possible, return the original question
        if not decomposed:
            decomposed.append(
                DecomposedQuestion(
                    sub_question=question,
                    reasoning_step=1,
                    dependency_indices=[],
                    question_type="analytical",
                    complexity_score=0.5,
                )
            )

        # Return a proper QuestionDecomposition object
        return QuestionDecomposition(sub_questions=decomposed)

    def _determine_question_type(self, question: str) -> str:
        """Determine the type of a question.

        Args:
            question: The question to classify.

        Returns:
            Question type as a string.
        """
        q_lower = question.lower()

        if any(word in q_lower for word in ["what", "define", "meaning"]):
            return "definition"
        elif any(word in q_lower for word in ["compare", "differ", "versus"]):
            return "comparison"
        elif any(word in q_lower for word in ["why", "cause", "reason"]):
            return "causal"
        elif any(word in q_lower for word in ["how", "steps", "process"]):
            return "procedural"
        else:
            return "analytical"

    def _extract_main_concept(self, question: str) -> str:
        """Extract the main concept from a causal question.

        Args:
            question: The question to extract concept from.

        Returns:
            The main concept as a string.
        """
        # Simple heuristic to extract key terms
        # For "Why does regularization prevent overfitting in neural networks?"
        # Extract "regularization" and "overfitting"
        question.lower()

        # Remove question words and common words
        stop_words = {"why", "does", "how", "what", "is", "the", "in", "of", "to", "a", "an", "and", "or", "but", "?"}
        words = [word.strip("?.,;:!") for word in question.split() if word.lower() not in stop_words]

        # Take first few meaningful words
        if len(words) >= 2:
            return f"{words[0]} and {words[1]}"
        elif len(words) == 1:
            return words[0]
        else:
            return "the concept"


__all__ = ["QuestionDecomposer"]
