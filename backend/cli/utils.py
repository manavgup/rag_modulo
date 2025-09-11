"""Utility functions for CLI search testing."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

console = Console()


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string."""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.1f}s"


def calculate_retrieval_metrics(query_results: list[Any]) -> dict[str, float]:
    """Calculate retrieval quality metrics."""
    if not query_results:
        return {"precision": 0.0, "avg_score": 0.0, "max_score": 0.0, "min_score": 0.0, "score_variance": 0.0}

    scores = [qr.score for qr in query_results if hasattr(qr, "score")]

    if not scores:
        return {"precision": 0.0, "avg_score": 0.0, "max_score": 0.0, "min_score": 0.0, "score_variance": 0.0}

    avg_score = sum(scores) / len(scores)
    variance = sum((s - avg_score) ** 2 for s in scores) / len(scores) if len(scores) > 1 else 0

    return {
        "precision": len([s for s in scores if s > 0.5]) / len(scores),  # Assuming 0.5 as relevance threshold
        "avg_score": avg_score,
        "max_score": max(scores),
        "min_score": min(scores),
        "score_variance": variance,
    }


def evaluate_answer_quality(answer: str, expected_keywords: list[str] | None = None) -> dict[str, Any]:
    """Evaluate answer quality based on various metrics."""
    metrics = {
        "length": len(answer),
        "word_count": len(answer.split()),
        "has_content": len(answer.strip()) > 0,
        "completeness_score": 0.0,
    }

    # Basic completeness heuristic
    if metrics["word_count"] < 10:
        metrics["completeness_score"] = 0.2
    elif metrics["word_count"] < 50:
        metrics["completeness_score"] = 0.5
    elif metrics["word_count"] < 100:
        metrics["completeness_score"] = 0.8
    else:
        metrics["completeness_score"] = 1.0

    # Check for expected keywords if provided
    if expected_keywords:
        keywords_found = [kw for kw in expected_keywords if kw.lower() in answer.lower()]
        metrics["keyword_coverage"] = float(len(keywords_found) / len(expected_keywords))
        metrics["keywords_found"] = keywords_found  # type: ignore[assignment]
        metrics["keywords_missing"] = [kw for kw in expected_keywords if kw not in keywords_found]  # type: ignore[assignment]

    return metrics


def compare_search_configs(results: list[dict[str, Any]]) -> Table:
    """Compare results from different search configurations."""
    table = Table(title="Configuration Comparison", show_header=True, header_style="bold magenta")

    table.add_column("Configuration", style="cyan", no_wrap=True)
    table.add_column("Avg Quality", style="yellow")
    table.add_column("Avg Time", style="green")
    table.add_column("Success Rate", style="blue")
    table.add_column("Avg Docs", style="magenta")

    # Group results by configuration
    configs: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        config = result.get("config", "default")
        if config not in configs:
            configs[config] = []
        configs[config].append(result)

    # Calculate metrics for each configuration
    for config, config_results in configs.items():
        successful = [r for r in config_results if r.get("success", False)]

        if successful:
            avg_quality = sum(r.get("quality_score", 0) for r in successful) / len(successful)
            avg_time = sum(r.get("execution_time", 0) for r in successful) / len(successful)
            success_rate = len(successful) / len(config_results) * 100
            avg_docs = sum(r.get("documents_retrieved", 0) for r in successful) / len(successful)

            table.add_row(config, f"{avg_quality:.1f}%", format_duration(avg_time), f"{success_rate:.1f}%", f"{avg_docs:.1f}")

    return table


def generate_quality_report(results: list[dict[str, Any]], output_path: str | None = None) -> str:
    """Generate comprehensive quality report."""
    report_lines = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report_lines.append("=" * 80)
    report_lines.append("RAG SEARCH QUALITY REPORT")
    report_lines.append(f"Generated: {timestamp}")
    report_lines.append("=" * 80)
    report_lines.append("")

    # Summary statistics
    total = len(results)
    successful = sum(1 for r in results if r.get("success", False))
    failed = total - successful

    report_lines.append("SUMMARY")
    report_lines.append("-" * 40)
    report_lines.append(f"Total Queries Tested: {total}")
    report_lines.append(f"Successful: {successful} ({successful/total*100:.1f}%)")
    report_lines.append(f"Failed: {failed} ({failed/total*100:.1f}%)")
    report_lines.append("")

    if successful > 0:
        # Quality metrics
        avg_quality = sum(r.get("quality_score", 0) for r in results if r.get("success", False)) / successful
        max_quality = max(r.get("quality_score", 0) for r in results if r.get("success", False))
        min_quality = min(r.get("quality_score", 0) for r in results if r.get("success", False))

        report_lines.append("QUALITY METRICS")
        report_lines.append("-" * 40)
        report_lines.append(f"Average Quality Score: {avg_quality:.1f}%")
        report_lines.append(f"Maximum Quality Score: {max_quality:.1f}%")
        report_lines.append(f"Minimum Quality Score: {min_quality:.1f}%")
        report_lines.append("")

        # Performance metrics
        times = [r.get("execution_time", 0) for r in results if r.get("success", False) and r.get("execution_time")]
        if times:
            avg_time = sum(times) / len(times)
            max_time = max(times)
            min_time = min(times)

            report_lines.append("PERFORMANCE METRICS")
            report_lines.append("-" * 40)
            report_lines.append(f"Average Execution Time: {format_duration(avg_time)}")
            report_lines.append(f"Maximum Execution Time: {format_duration(max_time)}")
            report_lines.append(f"Minimum Execution Time: {format_duration(min_time)}")
            report_lines.append("")

        # Retrieval metrics
        docs_counts = [r.get("documents_retrieved", 0) for r in results if r.get("success", False)]
        avg_docs = sum(docs_counts) / len(docs_counts) if docs_counts else 0

        report_lines.append("RETRIEVAL METRICS")
        report_lines.append("-" * 40)
        report_lines.append(f"Average Documents Retrieved: {avg_docs:.1f}")
        report_lines.append(f"Queries with No Results: {sum(1 for d in docs_counts if d == 0)}")
        report_lines.append("")

    # Failed queries
    if failed > 0:
        report_lines.append("FAILED QUERIES")
        report_lines.append("-" * 40)
        for result in results:
            if not result.get("success", False):
                report_lines.append(f"- Query: {result.get('query', 'Unknown')}")
                report_lines.append(f"  Error: {result.get('error', 'Unknown error')}")
        report_lines.append("")

    # Category breakdown if available
    categories = {}
    for result in results:
        cat = result.get("category", "uncategorized")
        if cat not in categories:
            categories[cat] = {"total": 0, "successful": 0, "quality_sum": 0}
        categories[cat]["total"] += 1
        if result.get("success", False):
            categories[cat]["successful"] += 1
            categories[cat]["quality_sum"] += result.get("quality_score", 0)

    if len(categories) > 1:
        report_lines.append("CATEGORY BREAKDOWN")
        report_lines.append("-" * 40)
        for cat, stats in categories.items():
            success_rate = stats["successful"] / stats["total"] * 100 if stats["total"] > 0 else 0
            avg_quality = stats["quality_sum"] / stats["successful"] if stats["successful"] > 0 else 0
            report_lines.append(f"{cat}:")
            report_lines.append(f"  Total: {stats['total']}")
            report_lines.append(f"  Success Rate: {success_rate:.1f}%")
            report_lines.append(f"  Avg Quality: {avg_quality:.1f}%")
        report_lines.append("")

    report_lines.append("=" * 80)

    report_text = "\n".join(report_lines)

    # Save to file if path provided
    if output_path:
        with open(output_path, "w") as f:
            f.write(report_text)
        console.print(f"[green]Report saved to {output_path}[/green]")

    return report_text


def load_test_queries(file_path: str) -> list[dict[str, Any]]:
    """Load test queries from JSON file."""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Test queries file not found: {file_path}")

    with open(path) as f:
        data: Any = json.load(f)

    # Support both 'test_queries' and direct list format
    if isinstance(data, list):
        return data  # type: ignore[no-any-return]
    elif isinstance(data, dict) and "test_queries" in data:
        return data["test_queries"]  # type: ignore[no-any-return]
    else:
        raise ValueError("Invalid test queries format. Expected list or dict with 'test_queries' key.")


def validate_collection_access(collection_id: str, db: Any, settings: Any) -> bool:
    """Validate that collection exists and is accessible."""

    from rag_solution.services.collection_service import CollectionService

    try:
        collection_service = CollectionService(db, settings)
        collection = collection_service.get_collection(uuid.UUID(collection_id))
        return collection is not None
    except Exception:
        return False
