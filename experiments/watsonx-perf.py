import asyncio
import logging
import time
import random
import string
from typing import List, Dict, Optional
from dataclasses import dataclass
from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ModelConfig:
    project_id: str = "3f77f23d-71b7-426b-ae13-bc4710769880"
    api_key: str = "vOP8jN6QNnWXR2HJGguzs1AvGOdadZY3_ppjwV-jJfjg"
    url: str = "https://us-south.ml.cloud.ibm.com"
    model_id: str = "meta-llama/llama-3-1-8b-instruct"

def get_model(config: ModelConfig) -> ModelInference:
    client = APIClient(
        project_id=config.project_id,
        credentials=Credentials(api_key=config.api_key, url=config.url)
    )
    
    model = ModelInference(
        persistent_connection=True,
        model_id=config.model_id,
        params={
            GenParams.MAX_NEW_TOKENS: 150,
            GenParams.TEMPERATURE: 0.7,
        },
        project_id=config.project_id,
        credentials=Credentials(api_key=config.api_key, url=config.url)
    )
    model.set_api_client(client)
    return model

def generate_dummy_text(min_words: int = 100, max_words: int = 200) -> str:
    word_count = random.randint(min_words, max_words)
    words = []
    for _ in range(word_count):
        word_length = random.randint(3, 10)
        word = ''.join(random.choices(string.ascii_lowercase, k=word_length))
        words.append(word)
    return ' '.join(words)

def generate_dummy_dataset(num_chunks: int = 50) -> List[str]:
    return [generate_dummy_text() for _ in range(num_chunks)]

async def process_chunks(texts: List[str], model: ModelInference, batch_size: int = 10) -> Dict:
    stats = {
        'total_time': 0,
        'batch_times': [],
        'total_chunks': len(texts),
        'total_batches': (len(texts) + batch_size - 1) // batch_size
    }
    
    start_time = time.time()
    all_responses = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        batch_start = time.time()
        
        queries = ["Generate 5 questions about this content" for _ in batch]
        try:
            responses = model.generate_text(
                prompt=queries,
                concurrency_limit=10
            )
            if isinstance(responses, dict) and 'results' in responses:
                batch_responses = [r['generated_text'] for r in responses['results']]
            elif isinstance(responses, list):
                batch_responses = [r['generated_text'] if isinstance(r, dict) else r for r in responses]
            else:
                batch_responses = [responses]
                
            all_responses.extend(batch_responses)
            
        except Exception as e:
            logger.error(f"Error processing batch {i//batch_size}: {e}")
            continue
            
        batch_time = time.time() - batch_start
        stats['batch_times'].append(batch_time)
        logger.info(f"Batch {i//batch_size + 1}/{stats['total_batches']} processed in {batch_time:.2f}s")
        
    stats['total_time'] = time.time() - start_time
    stats['avg_batch_time'] = sum(stats['batch_times']) / len(stats['batch_times'])
    stats['responses'] = len(all_responses)
    
    return stats

async def main():
    # Configuration
    config = ModelConfig()
    model = get_model(config)
    
    # Generate test data
    chunk_sizes = [10, 50, 100]
    
    for size in chunk_sizes:
        logger.info(f"\nTesting with {size} chunks:")
        texts = generate_dummy_dataset(size)
        
        stats = await process_chunks(texts, model)
        
        logger.info(f"Results for {size} chunks:")
        logger.info(f"Total time: {stats['total_time']:.2f}s")
        logger.info(f"Average batch time: {stats['avg_batch_time']:.2f}s")
        logger.info(f"Responses generated: {stats['responses']}")
        logger.info(f"Average time per chunk: {stats['total_time']/size:.2f}s")

if __name__ == "__main__":
    asyncio.run(main())