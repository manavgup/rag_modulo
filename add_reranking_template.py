#!/usr/bin/env python3
"""Script to add RERANKING template to existing users who don't have one.

This is needed after Issue #510 fix, as existing users were created before
the RERANKING template was added to user initialization.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from rag_solution.schemas.prompt_template_schema import (
    PromptTemplateInput,
    PromptTemplateType,
)
from rag_solution.services.prompt_template_service import PromptTemplateService
from rag_solution.models.user import User
from rag_solution.file_management.database import get_db


def add_reranking_template_to_users():
    """Add RERANKING template to all users who don't have one."""
    db = next(get_db())
    try:
        # Get all users
        users = db.query(User).all()

        prompt_service = PromptTemplateService(db)

        for user in users:
            print(f"Checking user: {user.email} ({user.id})")

            # Check if user already has RERANKING template
            try:
                existing = prompt_service.get_by_type(user.id, PromptTemplateType.RERANKING)
                if existing:
                    print(f"  ✓ User already has RERANKING template")
                    continue
            except Exception:
                pass  # Template doesn't exist, create it

            # Create RERANKING template
            try:
                template = prompt_service.create_template(
                    PromptTemplateInput(
                        name="default-reranking-template",
                        user_id=user.id,
                        template_type=PromptTemplateType.RERANKING,
                        system_prompt=(
                            "You are a document relevance scorer. Rate how relevant each document is "
                            "to the given query on the specified scale. Only provide the numerical score."
                        ),
                        template_format=(
                            "Rate the relevance of this document to the query on a scale of 0-{scale}:\n\n"
                            "Query: {query}\n\n"
                            "Document: {document}\n\n"
                            "Relevance score:"
                        ),
                        input_variables={
                            "query": "The search query",
                            "document": "The document text to score",
                            "scale": "Maximum score value (e.g., 10 for 0-10 scale)",
                        },
                        example_inputs={
                            "query": "What is machine learning?",
                            "document": "Machine learning is a subset of artificial intelligence...",
                            "scale": "10",
                        },
                        is_default=True,
                        max_context_length=4000,
                        validation_schema={
                            "model": "PromptVariables",
                            "fields": {
                                "query": {"type": "str", "min_length": 1},
                                "document": {"type": "str", "min_length": 1},
                                "scale": {"type": "str", "min_length": 1},
                            },
                            "required": ["query", "document", "scale"],
                        },
                    )
                )
                print(f"  ✓ Created RERANKING template: {template.id}")
            except Exception as e:
                print(f"  ✗ Failed to create RERANKING template: {e}")
                continue

        db.commit()
        print("\n✓ Migration complete!")
    finally:
        db.close()


if __name__ == "__main__":
    print("\n🔧 Adding RERANKING template to existing users\n")
    add_reranking_template_to_users()
