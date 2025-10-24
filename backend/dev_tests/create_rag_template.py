"""Script to create RAG template with updated strict instructions."""

import os
import sys
from uuid import UUID

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from sqlalchemy.orm import Session

from core.config import get_settings
from rag_solution.file_management.database import get_db
from rag_solution.schemas.prompt_template_schema import PromptTemplateInput, PromptTemplateType
from rag_solution.services.prompt_template_service import PromptTemplateService


def create_rag_template_for_user(user_id: str):
    """Create RAG template with strict instructions."""
    settings = get_settings()

    # Get database session
    db_gen = get_db()
    db: Session = next(db_gen)

    try:
        service = PromptTemplateService(db)

        template_input = PromptTemplateInput(
            name="default-rag-template",
            user_id=UUID(user_id),
            template_type=PromptTemplateType.RAG_QUERY,
            system_prompt=(
                "You are a helpful AI assistant specializing in answering questions based on the given context.\n\n"
                "CRITICAL RULES - FOLLOW EXACTLY:\n"
                "1. Answer ONLY the specific question provided below\n"
                "2. Do NOT generate additional questions or 'Question:' / 'Answer:' pairs\n"
                "3. Do NOT include 'Question:' or 'Answer:' labels in your response\n"
                "4. Do NOT mention documents, sources, or your reasoning process\n"
                "5. Do NOT include phrases like 'Based on the analysis' or 'in the context of'\n"
                "6. Provide ONLY a direct, factual answer based on the context provided\n"
                "7. If the information is not in the context, say 'The information is not available in the provided documents.'\n\n"
                "Format your responses using Markdown for better readability:\n"
                "- Use **bold** for emphasis on key points\n"
                "- Use bullet points (- or *) for lists\n"
                "- Use numbered lists (1. 2. 3.) for sequential steps\n"
                "- Use `code blocks` for technical terms or code\n"
                "- Use proper headings (## or ###) for sections when appropriate\n"
                "- Keep answers well-structured and concise"
            ),
            template_format="{context}\n\n{question}",
            input_variables={
                "context": "Retrieved context for answering the question",
                "question": "User's question to answer",
            },
            example_inputs={
                "context": "Python was created by Guido van Rossum.",
                "question": "Who created Python?",
            },
            is_default=True,
            max_context_length=2048,
            validation_schema={
                "model": "PromptVariables",
                "fields": {
                    "context": {"type": "str", "min_length": 1},
                    "question": {"type": "str", "min_length": 1},
                },
                "required": ["context", "question"],
            },
        )

        template = service.create_template(template_input)
        print(f"✅ Created RAG template: {template.id}")
        print(f"   User ID: {template.user_id}")
        print(f"   Template type: {template.template_type}")
        print(f"   Name: {template.name}")

    finally:
        db.close()


if __name__ == "__main__":
    user_id = "ee76317f-3b6f-4fea-8b74-56483731f58c"
    print(f"Creating RAG template for user: {user_id}")
    create_rag_template_for_user(user_id)
