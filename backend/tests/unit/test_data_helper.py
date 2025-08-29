from pathlib import Path
from typing import Any

from vectordbs.data_types import Document, DocumentChunk


def get_test_data_path(filename: str) -> str:
    """Get the full path to a test data file."""
    return str(Path(__file__).parent / filename)


def load_research_ecosystem_chunks() -> list[dict[str, Any]]:
    """Load predefined chunks from the research ecosystem document."""
    return [
        {
            "text": """Canada's research ecosystem is a complex network of institutions, funding agencies, and researchers working together to advance knowledge and innovation. The ecosystem includes universities, government research facilities, private sector R&D labs, and various funding organizations like NSERC, CIHR, and SSHRC.""",
            "metadata": {"source": "research_overview", "section": "overview", "page": 1},
        },
        {
            "text": """Research Institutions include universities and colleges conducting fundamental and applied research, government research laboratories and facilities, private sector research and development centers, and non-profit research institutes.""",
            "metadata": {"source": "research_overview", "section": "institutions", "page": 1},
        },
        {
            "text": """Funding Sources include federal funding through tri-council agencies (NSERC, CIHR, SSHRC), provincial research funding programs, industry partnerships and private sector investment, international collaboration grants, and charitable foundations.""",
            "metadata": {"source": "research_overview", "section": "funding", "page": 1},
        },
        {
            "text": """Research Infrastructure includes advanced research facilities and equipment, high-performance computing resources, research databases and libraries, and specialized laboratories and testing facilities.""",
            "metadata": {"source": "research_overview", "section": "infrastructure", "page": 2},
        },
        {
            "text": """Human Capital comprises principal investigators and research leads, graduate students and postdoctoral fellows, research technicians and support staff, and research administrators and grant managers.""",
            "metadata": {"source": "research_overview", "section": "human_capital", "page": 2},
        },
        {
            "text": """The ecosystem faces several challenges including maintaining global competitiveness, securing sustainable funding, attracting and retaining top talent, balancing basic and applied research, improving knowledge translation, and enhancing collaboration between sectors.""",
            "metadata": {"source": "research_overview", "section": "challenges", "page": 3},
        },
        {
            "text": """Current priorities include strengthening international research partnerships, supporting early career researchers, advancing indigenous research, promoting open science initiatives, developing research talent, and accelerating innovation and commercialization.""",
            "metadata": {"source": "research_overview", "section": "priorities", "page": 3},
        },
    ]


def create_test_document(chunks: list[dict[str, Any]], doc_id: str = "test_doc") -> Document:
    """Create a Document object from a list of chunk dictionaries."""
    return Document(
        id=doc_id,
        chunks=[DocumentChunk(text=chunk["text"], metadata=chunk["metadata"]) for chunk in chunks],
        metadata={"title": "Canada Research Ecosystem Overview", "source": "test_data", "type": "research_document"},
    )


def get_expected_question_types() -> dict[str, list[str]]:
    """Get expected question types and examples for different aspects of the research ecosystem."""
    return {
        "overview": [
            "What are the main components of Canada's research ecosystem?",
            "How do different institutions collaborate within the ecosystem?",
            "What role do funding agencies play in the ecosystem?",
        ],
        "institutions": [
            "What types of research institutions exist in Canada?",
            "How do government research facilities contribute to the ecosystem?",
            "What is the role of private sector R&D labs?",
        ],
        "funding": [
            "How is research funded in Canada?",
            "What are the main funding sources for Canadian researchers?",
            "How do tri-council agencies support research?",
        ],
        "infrastructure": [
            "What research infrastructure is available in Canada?",
            "How do researchers access specialized facilities?",
            "What role does high-performance computing play?",
        ],
        "human_capital": [
            "Who are the key personnel in research institutions?",
            "What support is available for graduate students?",
            "How are research teams typically structured?",
        ],
        "challenges": [
            "What challenges does the research ecosystem face?",
            "How is talent retention being addressed?",
            "What barriers exist in knowledge translation?",
        ],
        "priorities": [
            "What are the current research priorities in Canada?",
            "How is indigenous research being supported?",
            "What initiatives promote open science?",
        ],
    }


def validate_generated_questions(generated_questions: list[str], expected_types: dict[str, list[str]]) -> bool:
    """
    Validate that generated questions cover expected types and follow patterns.

    Args:
        generated_questions: List of questions generated by the suggester
        expected_types: Dictionary of question types and example patterns

    Returns:
        bool: True if questions meet expectations, False otherwise
    """
    if not generated_questions:
        return False

    # Check if questions start with question words
    question_words = {"what", "how", "who", "why", "where", "when", "which"}
    if not all(any(q.lower().startswith(word) for word in question_words) for q in generated_questions):
        return False

    # Check if questions end with question marks
    if not all(q.strip().endswith("?") for q in generated_questions):
        return False

    # Check coverage of different aspects
    covered_aspects = set()
    for question in generated_questions:
        for aspect, patterns in expected_types.items():
            if any(pattern.lower() in question.lower() for pattern in patterns):
                covered_aspects.add(aspect)

    # Should cover at least 3 different aspects
    return len(covered_aspects) >= 3
