import pytest
import os
import logging
import asyncio
import json
from rag_solution.pipeline.pipeline import Pipeline, PipelineResult
from rag_solution.data_ingestion.ingestion import DocumentStore
from vectordbs.factory import get_datastore
from vectordbs.error_types import CollectionError
from rag_solution.retrieval.factories import RetrieverFactory
from rag_solution.generation.factories import GeneratorFactory, EvaluatorFactory
from backend.core.config import settings

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest.fixture(scope="module")
def test_config():
    return {
        'query_rewriting': {
            'use_simple_rewriter': True,
            'use_hyponym_rewriter': False
        },
        'retrieval': {
            'type': 'vector',
            'vector_weight': 0.7
        },
        'generation': {
            'type': 'watsonx',
            'model_name': 'ibm/granite-13b-chat-v2',
            'default_params': {
                'max_new_tokens': 150,
                'temperature': 0.7
            },
            'api_key': settings.genai_key,
            'api_endpoint': settings.api_endpoint
        },
        'vector_store': 'milvus',
        'data_source': ['/Users/mg/Downloads/IBM_Annual_Report_2022.pdf'],
        'collection_name': 'test_ibm_annual_report',
        'top_k': 5,
    }

@pytest.fixture(scope="module")
def canada_research_config(test_config):
    config = test_config.copy()
    config['data_source'] = ['/Users/mg/Downloads/Canada_research_ecosystem_2024.pdf']
    config['collection_name'] = 'test_canada_research_ecosystem'
    return config

@pytest.fixture(scope="module")
async def test_pipeline(test_config):
    pipeline = Pipeline(test_config)
    await pipeline.initialize()
    return pipeline

@pytest.fixture(scope="module")
async def canada_research_pipeline(canada_research_config):
    vector_store = get_datastore(canada_research_config['vector_store'])
    collection_name = canada_research_config['collection_name']
    try:
        vector_store.delete_collection(collection_name)
    except CollectionError:
        pass  # Collection doesn't exist, which is fine
    vector_store.create_collection(collection_name)

    pipeline = Pipeline(canada_research_config)
    await pipeline.initialize()
    return pipeline

@pytest.mark.asyncio
async def test_document_ingestion(test_config):
    vector_store = get_datastore(test_config['vector_store'])
    document_store = DocumentStore(vector_store, test_config['collection_name'])
    
    try:
        # Debug: Check if the file exists
        file_path = '/Users/mg/Downloads/IBM_Annual_Report_2022.pdf'
        logger.info(f"File exists: {os.path.exists(file_path)}")
                
        # Load documents
        await document_store.load_documents(test_config['data_source'])
        
        # Verify that documents were ingested
        documents = document_store.get_documents()
        assert len(documents) > 0, "No documents were ingested"
        
        # Log successful ingestion
        logger.info(f"Documents successfully ingested into collection '{test_config['collection_name']}'")
        logger.info(f"Ingested {len(documents)} documents")
        logger.info(f"First document content: {documents[0].content[:100]}...")  # Log a snippet of the first document
        
    except Exception as e:
        logger.error(f"Error during document ingestion test: {str(e)}")
        raise
    finally:
        # Attempt to clean up the collection
        try:
            await document_store.clear()
            logger.info(f"Cleaned up test collection '{test_config['collection_name']}'")
        except Exception as cleanup_error:
            logger.warning(f"Failed to clean up test collection '{test_config['collection_name']}': {str(cleanup_error)}")

@pytest.mark.asyncio
async def test_query_processing(test_pipeline):
    try:
        query = "What were IBM's total revenues in 2022?"
        logger.info(f"Starting query processing for: {query}")
        
        logger.info("Initializing pipeline process")
        result = test_pipeline.process(query, test_pipeline.collection_name)
        
        logger.info("Pipeline process completed. Checking results...")
        
        assert isinstance(result, PipelineResult), "Result should be a PipelineResult object"
        assert result.original_query == query, "Original query mismatch"
        assert result.rewritten_query, "Rewritten query is empty"
        assert result.retrieved_documents, "No documents were retrieved"
        assert result.generated_answer, "No answer was generated"
        assert result.evaluation is not None, "Evaluation is missing"
        
        logger.info(f"Retrieved {len(result.retrieved_documents)} documents")
        assert len(result.retrieved_documents) > 0, "No documents were retrieved"
        
        logger.info(f"Response length: {len(result.generated_answer)}")
        assert len(result.generated_answer) > 50, "Response should be substantial"
        
        logger.info(f"Checking response content...")
        assert 'revenue' in result.generated_answer.lower(), "Response should mention revenue"
        assert '2022' in result.generated_answer, "Response should mention the year 2022"
        
        logger.info(f"Processed query: {query}")
        logger.info(f"Rewritten query: {result.rewritten_query}")
        logger.info(f"Response: {result.generated_answer[:100]}...")
        logger.info(f"Evaluation: {result.evaluation}")
    
    except Exception as e:
        logger.error(f"Error during query processing test: {str(e)}")
        logger.exception("Full traceback:")
        raise

@pytest.mark.asyncio
async def test_canada_research_query_processing(canada_research_pipeline):
    pipeline = await canada_research_pipeline
    questions = [
        "What are the three federal granting agencies mentioned in the document?",
        "What is the annual budget of the Canadian Institutes of Health Research (CIHR)?",
        "Which organization provides funding for infrastructure at Canadian universities and colleges?",
        "What is the vision of the Natural Sciences and Engineering Research Council (NSERC)?",
        "How much funding did the Government of Canada provide to CFI in March 2024?",
        "What is the mission of the National Research Council of Canada (NRC)?",
        "How many staff members does the NRC have as of 2023-24?",
        "What are the three departmental results for tracking and reporting against NRC's core responsibilities?",
        "Through which minister does the NRC report to Parliament?",
        "How many research centres are there under the NRC's R&D divisions?"
    ]
    
    results = []
    
    try:
        for query in questions:
            logger.info(f"Processing query: {query}")
            
            try:
                logger.debug(f"Calling pipeline.process with query: {query}")
                result = pipeline.process(query, pipeline.collection_name)
                logger.info(f"Pipeline process completed for query: {query}")
                
                logger.debug(f"Result object: {result}")
                logger.debug(f"Result type: {type(result)}")
                logger.debug(f"Result attributes: {dir(result)}")
                
                if isinstance(result, PipelineResult):
                    logger.debug(f"Retrieved documents count: {len(result.retrieved_documents)}")
                    logger.debug(f"Generated answer: {result.generated_answer}")
                    
                    results.append({
                        "query": query,
                        "original_query": result.original_query,
                        "rewritten_query": result.rewritten_query,
                        "generated_answer": result.generated_answer,
                        "evaluation": result.evaluation,
                        "retrieved_documents_count": len(result.retrieved_documents)
                    })
                    
                    logger.info(f"Processed query: {query}")
                    logger.info(f"Rewritten query: {result.rewritten_query}")
                    logger.info(f"Response: {result.generated_answer}...")
                    logger.info(f"Evaluation: {result.evaluation}")
                else:
                    logger.error(f"Unexpected result type for query '{query}': {type(result)}")
                    results.append({
                        "query": query,
                        "error": f"Unexpected result type: {type(result)}"
                    })
                
            except Exception as query_error:
                logger.error(f"Error processing query '{query}': {str(query_error)}")
                logger.exception("Query processing error traceback:")
                results.append({
                    "query": query,
                    "error": str(query_error)
                })
        
        # Write results to a JSON file
        with open('canada_research_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info("Results stored in canada_research_results.json")
        
        # Now perform assertions based on the stored results
        with open('canada_research_results.json', 'r') as f:
            stored_results = json.load(f)
        
        for result in stored_results:
            assert isinstance(result, dict), f"Stored result for query '{result['query']}' should be a dictionary"
            assert result["query"] in questions, f"Stored query '{result['query']}' should be in the original questions list"
            
            if "error" not in result:
                assert result["original_query"] == result["query"], f"Original query mismatch for '{result['query']}'"
                assert result["rewritten_query"], f"Rewritten query is empty for '{result['query']}'"
                assert result["generated_answer"], f"No answer was generated for '{result['query']}'"
                assert result["retrieved_documents_count"] > 0, f"No documents were retrieved for '{result['query']}'"
                assert len(result["generated_answer"]) > 50, f"Response should be substantial for '{result['query']}'"
            else:
                logger.error(f"Error in result for query '{result['query']}': {result['error']}")
            
            logger.info(f"Assertions passed for query: {result['query']}")
    
    except Exception as e:
        logger.error(f"Error during Canada research query processing test: {str(e)}")
        logger.exception("Full traceback:")
        raise

# ... [Keep all the existing code below] ...