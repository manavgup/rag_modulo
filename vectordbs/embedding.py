import logging
import os
import pickle
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import re
import PyPDF2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from genai import Client, Credentials
from genai.schema import (
    TextEmbeddingParameters,
    TextGenerationParameters,
    DecodingMethod,
)
from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)
from tqdm.notebook import tqdm
from unitxt import add_to_catalog
from unitxt.eval_utils import evaluate
from unitxt.metrics import MetricPipeline
from unitxt.operators import CopyFields

CHUNK_SIZE = 512
CHUNK_OVERLAP = 128

logging.getLogger("unitxt").setLevel(logging.ERROR)

load_dotenv(override=True)

creds = Credentials.from_env()
if creds.api_endpoint:
    print(f"Your API endpoint is: {creds.api_endpoint}")
    
client = Client(credentials=creds)

def get_embeddings(texts: list[str]):
    embeddings: list[list[str]] = []
    for response in client.text.embedding.create(
        model_id="sentence-transformers/all-minilm-l6-v2",
        inputs=texts,
        parameters=TextEmbeddingParameters(truncate_input_tokens=True),
    ):
        embeddings.extend(response.results)

    return embeddings

connections.connect(host="localhost", port="19530")
print(utility.get_server_version())

COLLECTION_NAME = "Test_collection"
INDEX_NAME = "Test_index"

# Run if you want to drop your old data
try:
    utility.drop_collection(COLLECTION_NAME)
    print("Collection has been deleted")
except:  # noqa: E722
    pass


id = FieldSchema(
    name="id",
    dtype=DataType.INT64,
    is_primary=True,
    auto_id=True,
)

text = FieldSchema(
    name="text",
    dtype=DataType.VARCHAR,
    max_length=4096,
)

text_vector = FieldSchema(name="text_vector", dtype=DataType.FLOAT_VECTOR, dim=384)

qid = FieldSchema(name="qid", dtype=DataType.INT64)

title = FieldSchema(
    name="title",
    dtype=DataType.VARCHAR,
    max_length=4096,
)

schema = CollectionSchema(
    fields=[id, text, text_vector, qid, title],
    description="Demo vector store",
    enable_dynamic_field=True,
)

collection = Collection(name=COLLECTION_NAME, schema=schema, using="default", shards_num=2)

def clean_text(text):
        # Remove unwanted characters, HTML tags, URLs, etc.
        cleaned_text = re.sub(r'<\/?[^>]*>', '', text)
        cleaned_text = re.sub(r'http\S+', '', cleaned_text)
        cleaned_text = re.sub(r'[\r\n\t]+', ' ', cleaned_text)
        return cleaned_text
    
def get_chunks(text):  # Helper function for chunking
        if len(text) <= CHUNK_SIZE:
            return [text]
        else:
            return [text[i:i + CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE - CHUNK_OVERLAP)]
        
def split_and_prepare_document_new(file_path: str):
    with open(file_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        
        embeddings = []
        for page in pdf_reader.pages:
            text = page.extract_text()
            cleaned_text = clean_text(text)
            chunks = get_chunks(cleaned_text)
            
            embedding = get_embeddings(chunks)
            embeddings.extend(embedding)
        
        return embeddings
    
def process_batch(document_list):
    batch_results = []

    for id, title, text in zip(
        document_list["id"].values.tolist(),
        document_list["title"].values.tolist(),
        document_list["text"].values.tolist(),
    ):
        for sub_text, sub_id, sub_title, sub_embedding in zip(*split_and_prepare_document_new(id, title, text)):
            batch_results.append(tuple((sub_id, sub_title, sub_text, sub_embedding)))
    return batch_results

%%time

batch_size = 10
processed_docs = []
cache_filename = Path("data/.cache/rag-1.2-prepared-docs.pkl")
allow_cache = True

if allow_cache and cache_filename.exists():
    print("Prepared docs cache file exists, loading.")
    with open(cache_filename, "rb+") as f:
        processed_docs = pickle.load(f)

    print("Processed docs loaded from pickle checkpoint")
else:
    for i in tqdm(range(0, len(documents), batch_size), desc="Processing Documents in Batches"):
        # find end of batch
        i_end = min(i + batch_size, len(documents))
        documents_batch = documents[i:i_end]

        # Process the batch
        processed = process_batch(documents_batch)
        processed_docs.extend(processed)

    # Save results for potential reuse
    cache_filename.parent.mkdir(exist_ok=True, parents=True)
    with open(cache_filename, "wb+") as f:
        pickle.dump(processed_docs, f)

    print("Processed docs saved to pickle checkpoint")