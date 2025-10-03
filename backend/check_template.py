"""Script to check RAG prompt template for a user."""
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

with Session(engine) as session:
    # Get all RAG templates
    stmt = select(PromptTemplate).where(PromptTemplate.template_type == PromptTemplateType.RAG_QUERY)
    templates = session.execute(stmt).scalars().all()

    print(f"Found {len(templates)} RAG templates\n")

    for template in templates:
        print(f"Template ID: {template.id}")
        print(f"User ID: {template.user_id}")
        print(f"Name: {template.name}")
        print(f"Is Default: {template.is_default}")
        print("\nSystem Prompt:")
        print(template.system_prompt)
        print("\nTemplate Format:")
        print(template.template_format)
        print("\n" + "=" * 80 + "\n")
