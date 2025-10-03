"""Script to update RAG template to prevent LLM from generating Q&A pairs."""
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

# Better system prompt that prevents Q&A generation
UPDATED_SYSTEM_PROMPT = """You are a helpful AI assistant that answers questions based on the provided context.

IMPORTANT INSTRUCTIONS:
- Answer ONLY the specific question asked
- Use ONLY the information from the provided context
- Do NOT generate additional questions
- Do NOT create question-answer pairs
- Do NOT add follow-up questions
- Provide a direct, focused answer"""

# Clean template format
UPDATED_TEMPLATE_FORMAT = """Context:
{context}

Question: {question}

Answer:"""

with Session(engine) as session:
    # Get all RAG templates
    stmt = select(PromptTemplate).where(PromptTemplate.template_type == PromptTemplateType.RAG_QUERY)
    templates = session.execute(stmt).scalars().all()

    print(f"Found {len(templates)} RAG templates\n")

    for template in templates:
        print(f"Updating template: {template.name} (ID: {template.id})")
        print(f"User ID: {template.user_id}\n")

        print("OLD System Prompt:")
        print(template.system_prompt)
        print("\nNEW System Prompt:")
        print(UPDATED_SYSTEM_PROMPT)

        print("\nOLD Template Format:")
        print(template.template_format)
        print("\nNEW Template Format:")
        print(UPDATED_TEMPLATE_FORMAT)

        template.system_prompt = UPDATED_SYSTEM_PROMPT
        template.template_format = UPDATED_TEMPLATE_FORMAT

        print("\n" + "=" * 80 + "\n")

    # Commit changes
    response = input("Do you want to apply these changes? (yes/no): ")
    if response.lower() == "yes":
        session.commit()
        print("\n✅ Templates updated successfully!")
        print("\nRestart your application for changes to take effect.")
    else:
        session.rollback()
        print("\n❌ Changes cancelled.")
