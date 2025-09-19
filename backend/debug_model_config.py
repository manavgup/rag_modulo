#!/usr/bin/env python3
"""Debug script to check model configuration."""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__)))

from core.config import get_settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from rag_solution.file_management.database import create_database_url
from rag_solution.services.llm_model_service import LLMModelService
from rag_solution.services.llm_provider_service import LLMProviderService


def main():
    """Check model configuration."""
    settings = get_settings()

    # Create database session
    engine = create_engine(create_database_url(settings))
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # Initialize services
        provider_service = LLMProviderService(db)
        model_service = LLMModelService(db)

        print("=== PROVIDER AND MODEL CONFIGURATION DEBUG ===")

        # Get WatsonX provider
        watsonx_provider = provider_service.get_provider_by_name("watsonx")
        if watsonx_provider:
            print(f"WatsonX Provider ID: {watsonx_provider.id}")
            print(f"WatsonX Provider Name: {watsonx_provider.name}")

            # Get models for this provider
            models = model_service.get_models_by_provider(watsonx_provider.id)
            print(f"\nModels for WatsonX provider ({len(models)} total):")
            for model in models:
                print(f"  Model ID: {model.id}")
                print(f"  Model Name: {model.model_id}")
                print(f"  Type: {model.model_type}")
                print(f"  Is Default: {model.is_default}")
                print(f"  Updated: {model.updated_at}")
                print("  ---")

            # Get default generation model
            default_gen_models = [m for m in models if m.is_default and str(m.model_type) == "ModelType.GENERATION"]
            print(f"\nDefault Generation Models: {len(default_gen_models)}")
            for model in default_gen_models:
                print(f"  DEFAULT: {model.model_id}")

            # Check if Meta Llama model exists
            meta_llama_models = [m for m in models if "meta-llama" in m.model_id.lower()]
            print(f"\nMeta Llama Models: {len(meta_llama_models)}")
            for model in meta_llama_models:
                print(f"  LLAMA: {model.model_id} (default: {model.is_default})")
        else:
            print("ERROR: WatsonX provider not found!")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
