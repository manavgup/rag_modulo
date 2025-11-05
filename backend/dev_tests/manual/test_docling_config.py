"""Quick test to check if Docling is enabled and importable."""
import sys
sys.path.insert(0, 'backend')

from core.config import get_settings

settings = get_settings()

print("=" * 60)
print("Docling Configuration Check")
print("=" * 60)
print(f"ENABLE_DOCLING: {settings.enable_docling}")
print(f"DOCLING_FALLBACK_ENABLED: {settings.docling_fallback_enabled}")
print()

# Try importing docling
print("Attempting to import docling...")
try:
    from docling.document_converter import DocumentConverter
    print("✅ SUCCESS: Docling imported successfully!")
    print(f"   DocumentConverter available: {DocumentConverter is not None}")
except ImportError as e:
    print(f"❌ FAILED: Could not import docling")
    print(f"   Error: {e}")
print()

# Check if DoclingProcessor can be initialized
print("Attempting to initialize DoclingProcessor...")
try:
    from rag_solution.data_ingestion.docling_processor import DoclingProcessor
    processor = DoclingProcessor(settings)
    if processor.converter is not None:
        print("✅ SUCCESS: DoclingProcessor initialized with converter")
    else:
        print("❌ FAILED: DoclingProcessor converter is None")
except Exception as e:
    print(f"❌ FAILED: Could not initialize DoclingProcessor")
    print(f"   Error: {e}")
print()

# Check DocumentProcessor routing
print("Checking DocumentProcessor routing...")
try:
    from rag_solution.data_ingestion.document_processor import DocumentProcessor
    doc_processor = DocumentProcessor(settings=settings)

    pdf_processor = doc_processor.processors.get('.pdf')
    print(f"PDF processor type: {type(pdf_processor).__name__}")

    if type(pdf_processor).__name__ == 'DoclingProcessor':
        print("✅ SUCCESS: PDF files will use DoclingProcessor")
    else:
        print(f"❌ FAILED: PDF files will use {type(pdf_processor).__name__} instead")

except Exception as e:
    print(f"❌ FAILED: Could not check DocumentProcessor")
    print(f"   Error: {e}")

print("=" * 60)
