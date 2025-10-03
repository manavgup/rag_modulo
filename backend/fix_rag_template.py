"""Script to fix RAG prompt templates by removing question generation instructions."""
import sys

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

# Add backend to path
sys.path.insert(0, "/Users/mg/mg-work/manav/work/ai-experiments/rag_modulo/backend")

from core.config import get_settings

from rag_solution.models.prompt_template import PromptTemplate
from rag_solution.schemas.prompt_template_schema import PromptTemplateType

settings = get_settings()

# Create database connection URL
db_url = (
    f"postgresql://{settings.collectiondb_user}:{settings.collectiondb_pass}"
    f"@{settings.collectiondb_host}:{settings.collectiondb_port}/{settings.collectiondb_name}"
)
engine = create_engine(db_url)

# Correct RAG template format
CORRECT_TEMPLATE_FORMAT = "{context}\n\n{question}"
CORRECT_SYSTEM_PROMPT = "You are a helpful AI assistant specializing in answering questions based on the given context."

with Session(engine) as session:
    # Get all RAG templates
    stmt = select(PromptTemplate).where(PromptTemplate.template_type == PromptTemplateType.RAG_QUERY)
    templates = session.execute(stmt).scalars().all()

    print(f"Found {len(templates)} RAG templates to check\n")

    for template in templates:
        print(f"Checking template: {template.name} (ID: {template.id}, User: {template.user_id})")

        needs_update = False

        # Check if template format contains question generation instructions
        if any(
            indicator in template.template_format.lower()
            for indicator in ["generate", "question-answer pair", "instruction", "diverse question"]
        ):
            print("  ⚠️  FOUND CONTAMINATED TEMPLATE FORMAT:")
            print(f"  Current: {template.template_format[:200]}...")
            needs_update = True
        else:
            print("  ✓ Template format looks clean")

        # Check system prompt
        if any(
            indicator in (template.system_prompt or "").lower()
            for indicator in ["generate question", "question-answer pair"]
        ):
            print("  ⚠️  FOUND CONTAMINATED SYSTEM PROMPT:")
            print(f"  Current: {template.system_prompt[:200]}...")
            needs_update = True

        if needs_update:
            print("\n  🔧 UPDATING template to clean version...")
            template.template_format = CORRECT_TEMPLATE_FORMAT
            template.system_prompt = CORRECT_SYSTEM_PROMPT
            print("  ✓ Updated successfully")

        print()

    # Commit changes
    response = input("\nDo you want to commit these changes? (yes/no): ")
    if response.lower() == "yes":
        session.commit()
        print("\n✅ Changes committed successfully!")
    else:
        session.rollback()
        print("\n❌ Changes rolled back. No modifications made.")
