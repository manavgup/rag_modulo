"""Debug script to see what Docling extracts from a PDF.

Usage:
    poetry run python dev_tests/manual/test_docling_debug.py
"""

from docling.document_converter import DocumentConverter  # type: ignore[import-not-found]


def main():
    """Debug Docling extraction."""
    pdf_path = "/Users/mg/Downloads/407ETR.pdf"

    print("=" * 80)
    print("DOCLING DEBUG - Raw Extraction")
    print("=" * 80)
    print(f"\n📄 Processing: {pdf_path}\n")

    # Convert with Docling
    converter = DocumentConverter()
    result = converter.convert(pdf_path)

    doc = result.document

    print("✅ Document converted successfully")
    print("\n📋 Document Metadata:")
    print(f"   - Has metadata attr: {hasattr(doc, 'metadata')}")
    if hasattr(doc, "metadata"):
        print(f"   - Metadata: {doc.metadata}")

    print("\n🔍 Document Structure:")
    print(f"   - Has iterate_items: {hasattr(doc, 'iterate_items')}")

    if hasattr(doc, "iterate_items"):
        items = list(doc.iterate_items())
        print(f"   - Total items: {len(items)}")

        if items:
            print("\n📝 Item Types:")
            item_types = {}
            for item in items:
                item_type = type(item).__name__
                item_types[item_type] = item_types.get(item_type, 0) + 1

            for item_type, count in item_types.items():
                print(f"      - {item_type}: {count}")

            print("\n🔎 First 5 items (checking page info):")
            for i, item_data in enumerate(items[:5]):
                print(f"\n   --- Item {i + 1} ---")

                # Extract actual item from tuple
                if isinstance(item_data, tuple):
                    item = item_data[0]
                    level = item_data[1] if len(item_data) > 1 else None
                    print(f"   Tuple: (item, level={level})")
                else:
                    item = item_data
                    print("   Direct item")

                print(f"   Type: {type(item).__name__}")

                # Check for text
                if hasattr(item, "text"):
                    text = str(item.text)[:80]
                    print(f"   Text: {text}...")

                # Check for provenance (page info)
                if hasattr(item, "prov"):
                    prov = item.prov
                    print("   Has prov: True")
                    print(f"   Prov type: {type(prov)}")
                    print(f"   Prov value: {prov}")

                    # If it's a list, check first element
                    if isinstance(prov, list) and len(prov) > 0:
                        print(f"   Prov[0] type: {type(prov[0])}")
                        print(f"   Prov[0] value: {prov[0]}")
                        if hasattr(prov[0], "page"):
                            print(f"   Prov[0].page: {prov[0].page}")
                        if hasattr(prov[0], "__dict__"):
                            print(f"   Prov[0] attrs: {prov[0].__dict__}")
                else:
                    print("   Has prov: False")

                # Check for page_no attribute directly
                if hasattr(item, "page_no"):
                    print(f"   item.page_no: {item.page_no}")
                if hasattr(item, "page"):
                    print(f"   item.page: {item.page}")
                else:
                    print(f"   Attributes: {dir(item)[:10]}...")  # Show first 10 attrs

                    # Try to get text
                    if hasattr(item, "text"):
                        text = item.text[:100] if len(item.text) > 100 else item.text
                        print(f"   Text: {text}...")

                    # Try to get page
                    if hasattr(item, "prov"):
                        print(f"   Provenance: {item.prov}")
        else:
            print("   ⚠️  No items found!")
            print("\n   This could mean:")
            print("      1. PDF is image-based and needs OCR")
            print("      2. PDF structure isn't recognized")
            print("      3. Content is in a different format")

    # Check if we can export to markdown
    print("\n📄 Export Options:")
    if hasattr(doc, "export_to_markdown"):
        print("   - Has export_to_markdown")
        try:
            md = doc.export_to_markdown()
            print(f"   - Markdown length: {len(md)} chars")
            print(f"   - Markdown preview:\n{md[:500]}")
        except Exception as e:
            print(f"   - Export failed: {e}")

    if hasattr(doc, "export_to_text"):
        print("   - Has export_to_text")
        try:
            text = doc.export_to_text()
            print(f"   - Text length: {len(text)} chars")
            print(f"   - Text preview:\n{text[:500]}")
        except Exception as e:
            print(f"   - Export failed: {e}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
