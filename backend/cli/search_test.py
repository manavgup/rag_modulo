"""CLI tool for testing and diagnosing RAG search quality."""

import asyncio
import json
import time
import uuid
from typing import Any
from pydantic import UUID4

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()

# Delay imports that require configuration until needed
def get_logger_lazy():
    from core.logging_utils import get_logger
    return get_logger("cli.search_test")

def get_services():
    from rag_solution.file_management.database import get_db
    from rag_solution.query_rewriting.query_rewriter import (
        HypotheticalDocumentEmbedding,
        QueryRewriter,
        SimpleQueryRewriter,
    )
    from rag_solution.retrieval.retriever import HybridRetriever, VectorRetriever
    from rag_solution.schemas.search_schema import SearchInput, SearchOutput
    from rag_solution.services.collection_service import CollectionService
    from rag_solution.services.pipeline_service import PipelineService
    from rag_solution.services.search_service import SearchService
    from vectordbs.factory import get_datastore
    from vectordbs.vector_store import VectorStore

    return {
        "get_db": get_db,
        "SearchInput": SearchInput,
        "SearchOutput": SearchOutput,
        "SearchService": SearchService,
        "PipelineService": PipelineService,
        "CollectionService": CollectionService,
        "QueryRewriter": QueryRewriter,
        "SimpleQueryRewriter": SimpleQueryRewriter,
        "HypotheticalDocumentEmbedding": HypotheticalDocumentEmbedding,
        "VectorRetriever": VectorRetriever,
        "HybridRetriever": HybridRetriever,
        "VectorStore": VectorStore,
        "get_datastore": get_datastore,
    }


@click.group()
def search():
    """RAG search testing commands."""


@search.command()
@click.option("--query", "-q", required=True, help="Search query to test")
@click.option("--collection-id", "-c", required=True, help="Collection UUID")
@click.option("--pipeline-id", "-p", help="Pipeline UUID (optional)")
@click.option("--user-id", "-u", required=True, help="User UUID")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed pipeline metrics")
@click.option("--output", "-o", type=click.Path(), help="Save results to JSON file")
def test(query: str, collection_id: str, pipeline_id: str | None, user_id: str, verbose: bool, output: str | None):
    """Test search query and analyze results."""
    asyncio.run(_test_search(query, collection_id, pipeline_id, user_id, verbose, output))


async def _test_search(query: str, collection_id: str, pipeline_id: str | None, user_id: str, verbose: bool, output: str | None):
    """Execute search test with detailed metrics."""
    start_time = time.time()

    console.print("\n[bold cyan]🔍 Testing Search Query[/bold cyan]")
    console.print(f"Query: [yellow]{query}[/yellow]")
    console.print(f"Collection: {collection_id}")
    if pipeline_id:
        console.print(f"Pipeline: {pipeline_id}")
    console.print(f"User: {user_id}\n")

    # Get services and database
    services = get_services()
    db = next(services["get_db"]())
    logger = get_logger_lazy()

    try:
        # Initialize services
        search_service = services["SearchService"](db)

        # Create search input
        search_input = services["SearchInput"](
            question=query,
            collection_id=uuid.UUID(collection_id),
            pipeline_id=uuid.UUID(pipeline_id) if pipeline_id else None,
            user_id=uuid.UUID(user_id)
        )

        # Execute search with progress indicator
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            progress.add_task("Executing search...", total=None)

            # Perform search
            result = await search_service.search(search_input)

            progress.stop()

        # Calculate metrics
        execution_time = time.time() - start_time

        # Display results
        _display_results(result, execution_time, verbose)

        # Save to file if requested
        if output:
            _save_results(result, execution_time, output)
            console.print(f"\n[green]✅ Results saved to {output}[/green]")

        return result

    except Exception as e:
        console.print(f"\n[red]❌ Search failed: {e!s}[/red]")
        logger.error(f"Search test failed: {e!s}", exc_info=True)
        raise
    finally:
        db.close()


def _display_results(result: Any, execution_time: float, verbose: bool):
    """Display search results with formatting."""

    # Answer section
    console.print("\n[bold green]📝 Generated Answer:[/bold green]")
    console.print(result.answer)

    # Metrics section
    console.print("\n[bold blue]📊 Search Metrics:[/bold blue]")
    metrics_table = Table(show_header=True, header_style="bold magenta")
    metrics_table.add_column("Metric", style="cyan")
    metrics_table.add_column("Value", style="yellow")

    metrics_table.add_row("Execution Time", f"{execution_time:.2f}s")
    metrics_table.add_row("Documents Retrieved", str(len(result.documents) if result.documents else 0))
    metrics_table.add_row("Query Results", str(len(result.query_results) if result.query_results else 0))

    if result.rewritten_query:
        metrics_table.add_row("Rewritten Query", result.rewritten_query)

    if result.evaluation:
        metrics_table.add_row("Evaluation Score", str(result.evaluation.get("score", "N/A")))
        metrics_table.add_row("Evaluation Feedback", str(result.evaluation.get("feedback", "N/A")))

    console.print(metrics_table)

    # Verbose mode - show retrieved documents
    if verbose and result.documents:
        console.print("\n[bold cyan]📚 Retrieved Documents:[/bold cyan]")
        for idx, doc in enumerate(result.documents, 1):
            console.print(f"\n[yellow]Document {idx}:[/yellow]")
            console.print(f"  ID: {doc.get('id', 'N/A')}")
            console.print(f"  Score: {doc.get('score', 'N/A')}")
            if "text" in doc:
                text_preview = doc["text"][:200] + "..." if len(doc["text"]) > 200 else doc["text"]
                console.print(f"  Text: {text_preview}")

    # Show metadata if available
    if verbose and result.metadata:
        console.print("\n[bold magenta]🔧 Pipeline Metadata:[/bold magenta]")
        for key, value in result.metadata.items():
            console.print(f"  {key}: {value}")


def _save_results(result: Any, execution_time: float, output_path: str):
    """Save search results to JSON file."""
    output_data = {
        "query": result.question if hasattr(result, "question") else None,
        "answer": result.answer,
        "execution_time": execution_time,
        "documents_count": len(result.documents) if result.documents else 0,
        "rewritten_query": result.rewritten_query,
        "evaluation": result.evaluation,
        "metadata": result.metadata,
        "documents": result.documents if result.documents else [],
        "query_results": [
            {
                "chunk_id": qr.chunk.chunk_id if qr.chunk else None,
                "score": qr.score,
                "text": qr.chunk.text if qr.chunk else None
            }
            for qr in (result.query_results or [])
        ]
    }

    with open(output_path, "w") as f:
        json.dump(output_data, f, indent=2, default=str)


@search.command()
@click.option("--query", "-q", required=True, help="Search query to test")
@click.option("--collection-id", "-c", required=True, help="Collection UUID")
@click.option("--strategy", "-s", type=click.Choice(["simple", "hypothetical"]), default="simple", help="Query rewriting strategy")
def test_components(query: str, collection_id: str, strategy: str):
    """Test individual pipeline components."""
    asyncio.run(_test_components(query, collection_id, strategy))


async def _test_components(query: str, collection_id: str, strategy: str):
    """Test each RAG pipeline component individually."""

    console.print("\n[bold cyan]🔧 Component Testing[/bold cyan]")
    console.print(f"Query: [yellow]{query}[/yellow]")
    console.print(f"Collection: {collection_id}\n")

    services = get_services()
    db = next(services["get_db"]())
    logger = get_logger_lazy()

    try:
        # Test 1: Query Rewriting
        console.print("[bold green]1️⃣ Testing Query Rewriting[/bold green]")

        if strategy == "simple":
            rewriter = services["SimpleQueryRewriter"]({})
        else:
            rewriter = services["HypotheticalDocumentEmbedding"]({})

        start = time.time()
        rewritten = await rewriter.rewrite(query)
        rewrite_time = time.time() - start

        console.print(f"  Original: {query}")
        console.print(f"  Rewritten: {rewritten}")
        console.print(f"  Time: {rewrite_time:.3f}s\n")

        # Test 2: Document Retrieval
        console.print("[bold green]2️⃣ Testing Document Retrieval[/bold green]")

        # Initialize vector store
        collection_service = services["CollectionService"](db)
        collection = collection_service.get_collection_by_id(uuid.UUID(collection_id))

        if not collection:
            console.print("[red]Collection not found![/red]")
            return

        vector_store = services["get_datastore"](collection.vector_db_name)
        vector_store.initialize(collection_name=collection.name)

        # Test retrieval
        retriever = services["VectorRetriever"](vector_store)

        start = time.time()
        results = await retriever.retrieve(rewritten, top_k=5)
        retrieval_time = time.time() - start

        console.print(f"  Documents retrieved: {len(results)}")
        console.print(f"  Time: {retrieval_time:.3f}s")

        if results:
            console.print(f"  Top score: {results[0].score:.4f}")
            console.print(f"  Avg score: {sum(r.score for r in results) / len(results):.4f}\n")

        # Test 3: Context Formatting
        console.print("[bold green]3️⃣ Testing Context Formatting[/bold green]")

        if results:
            context_parts = []
            for idx, result in enumerate(results[:3], 1):
                context_parts.append(f"[Document {idx}]\n{result.chunk.text}")

            context = "\n\n".join(context_parts)
            console.print(f"  Context length: {len(context)} characters")
            console.print(f"  Number of chunks: {len(context_parts)}")

            # Show preview
            preview = context[:300] + "..." if len(context) > 300 else context
            console.print(f"\n  Context preview:\n  {preview}")

        # Summary
        console.print("\n[bold blue]📊 Component Test Summary[/bold blue]")
        summary_table = Table(show_header=True, header_style="bold magenta")
        summary_table.add_column("Component", style="cyan")
        summary_table.add_column("Status", style="green")
        summary_table.add_column("Time", style="yellow")

        summary_table.add_row("Query Rewriting", "✅ Success", f"{rewrite_time:.3f}s")
        summary_table.add_row("Document Retrieval", "✅ Success" if results else "❌ No results", f"{retrieval_time:.3f}s")
        summary_table.add_row("Context Formatting", "✅ Success" if results else "⚠️ No context", "N/A")

        console.print(summary_table)

    except Exception as e:
        console.print(f"\n[red]❌ Component test failed: {e!s}[/red]")
        logger.error(f"Component test failed: {e!s}", exc_info=True)
        raise
    finally:
        db.close()


@search.command()
@click.option("--queries-file", "-f", required=True, type=click.Path(exists=True), help="JSON file with test queries")
@click.option("--collection-id", "-c", required=True, help="Collection UUID")
@click.option("--pipeline-id", "-p", help="Pipeline UUID (optional)")
@click.option("--user-id", "-u", required=True, help="User UUID")
@click.option("--output", "-o", type=click.Path(), help="Save batch results to JSON file")
def batch_test(queries_file: str, collection_id: str, pipeline_id: str | None, user_id: str, output: str | None):
    """Run batch testing with quality metrics."""
    asyncio.run(_batch_test(queries_file, collection_id, pipeline_id, user_id, output))


async def _batch_test(queries_file: str, collection_id: str, pipeline_id: str | None, user_id: str, output: str | None):
    """Execute batch testing on multiple queries."""

    # Load test queries
    with open(queries_file) as f:
        test_data = json.load(f)

    queries = test_data.get("test_queries", [])

    console.print("\n[bold cyan]📊 Batch Testing[/bold cyan]")
    console.print(f"Queries to test: {len(queries)}")
    console.print(f"Collection: {collection_id}\n")

    results = []

    # Process each query
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:

        for idx, test_case in enumerate(queries, 1):
            query = test_case.get("query", "")
            task = progress.add_task(f"Testing query {idx}/{len(queries)}: {query[:50]}...", total=None)

            try:
                # Execute search
                result = await _test_search(
                    query=query,
                    collection_id=collection_id,
                    pipeline_id=pipeline_id,
                    user_id=user_id,
                    verbose=False,
                    output=None
                )

                # Calculate quality metrics
                quality_score = _calculate_quality_score(result, test_case)

                results.append({
                    "query": query,
                    "category": test_case.get("category", "unknown"),
                    "success": True,
                    "answer_length": len(result.answer) if result.answer else 0,
                    "documents_retrieved": len(result.documents) if result.documents else 0,
                    "quality_score": quality_score,
                    "evaluation": result.evaluation
                })

            except Exception as e:
                results.append({
                    "query": query,
                    "category": test_case.get("category", "unknown"),
                    "success": False,
                    "error": str(e)
                })

            progress.remove_task(task)

    # Display summary
    _display_batch_summary(results)

    # Save results if requested
    if output:
        with open(output, "w") as f:
            json.dump(results, f, indent=2, default=str)
        console.print(f"\n[green]✅ Batch results saved to {output}[/green]")

    return results


def _calculate_quality_score(result: Any, test_case: dict[str, Any]) -> float:
    """Calculate quality score for search result."""
    score = 0.0
    max_score = 0.0

    # Check if answer exists
    if result.answer:
        score += 25
    max_score += 25

    # Check document retrieval
    if result.documents and len(result.documents) > 0:
        score += 25
    max_score += 25

    # Check for expected keywords
    expected_keywords = test_case.get("expected_keywords", [])
    if expected_keywords and result.answer:
        keywords_found = sum(1 for kw in expected_keywords if kw.lower() in result.answer.lower())
        score += (keywords_found / len(expected_keywords)) * 25
    max_score += 25

    # Check evaluation score if available
    if result.evaluation and "score" in result.evaluation:
        eval_score = result.evaluation["score"]
        if isinstance(eval_score, int | float):
            score += (eval_score / 100) * 25
    max_score += 25

    return (score / max_score) * 100 if max_score > 0 else 0


def _display_batch_summary(results: list[dict[str, Any]]):
    """Display summary of batch test results."""

    console.print("\n[bold blue]📈 Batch Test Summary[/bold blue]")

    # Calculate statistics
    total = len(results)
    successful = sum(1 for r in results if r.get("success", False))
    failed = total - successful

    if successful > 0:
        avg_quality = sum(r.get("quality_score", 0) for r in results if r.get("success", False)) / successful
        avg_docs = sum(r.get("documents_retrieved", 0) for r in results if r.get("success", False)) / successful
    else:
        avg_quality = 0
        avg_docs = 0

    # Display summary table
    summary_table = Table(show_header=True, header_style="bold magenta")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="yellow")

    summary_table.add_row("Total Queries", str(total))
    summary_table.add_row("Successful", f"{successful} ({successful/total*100:.1f}%)")
    summary_table.add_row("Failed", f"{failed} ({failed/total*100:.1f}%)")
    summary_table.add_row("Avg Quality Score", f"{avg_quality:.1f}%")
    summary_table.add_row("Avg Documents Retrieved", f"{avg_docs:.1f}")

    console.print(summary_table)

    # Show failures if any
    if failed > 0:
        console.print("\n[bold red]❌ Failed Queries:[/bold red]")
        for result in results:
            if not result.get("success", False):
                console.print(f"  - {result['query']}: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    search()
