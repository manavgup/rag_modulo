from pymilvus import (
    connections,
    utility,
    FieldSchema, CollectionSchema, DataType,
    Collection
)
from transformers import pipeline

import PyPDF2
from typing import List, Optional, Union, Sequence
from genai.client import Client
from genai.credentials import Credentials
from genai.schema import TextEmbeddingParameters, TextTokenizationParameters, TextTokenizationReturnOptions
from genai.schema import TextGenerationParameters, TextGenerationReturnOptions, DecodingMethod
from genai.text.tokenization import CreateExecutionOptions
from dotenv import load_dotenv
from dataclasses import dataclass
import re

load_dotenv()
client = Client(credentials=Credentials.from_env())
print ("client", client)   
# Documents
Document = str
Documents = List[Document]

Vector = Union[Sequence[float], Sequence[int]]
# Embeddings
Embedding = Vector
Embeddings = List[Embedding]

# Example threshold values
ENTITY_MATCH_THRESHOLD = 0.3  # Adjust based on empirical data
POS_MATCH_THRESHOLD = 0.3     # Adjust based on empirical data
TOKENIZER_DIM = 384

CHUNK_SIZE = 512
CHUNK_OVERLAP = 128
NLIST_SIZE = 1024

@dataclass
class RetrievedContext:
    id: int
    text: str
    distance: Optional[float] = None
    
class FileToMilvus:
    def __init__(self, collection_name, file_path, host='localhost', port='19530'):
        self.collection_name: str = collection_name
        self.file_path: str = file_path
        self.host: str = host
        self.port = port
        self._connect()
        self.tokenizer_model="sentence-transformers/all-minilm-l6-v2"
        self.embedding_model="sentence-transformers/all-minilm-l6-v2"
        self.ner_model="dslim/bert-base-NER"
        self.pos_model="vblagoje/bert-english-uncased-finetuned-pos"
        self.ner_pipeline = pipeline("token-classification", model=self.ner_model)
        #self.pos_pipeline = pipeline("token-classification", model=self.pos_model)

        self.max_length = 256
        self.stride = 128

    def _connect(self):
        connections.connect(default={"host": self.host, "port": self.port})
        self.client :Client = client
        
    def sliding_window_tokenize(self, text):
        tokenized_chunks = self.tokenizer(
            text,
            max_length=self.max_length,
            stride=self.stride,
            truncation=True,
            return_overflowing_tokens=True,
            padding='max_length',
            return_tensors='pt'
        )
        return tokenized_chunks
    
    def create_collection(self):
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="embeddings", dtype=DataType.FLOAT_VECTOR, dim=TOKENIZER_DIM),
            FieldSchema(name="cleaned_text", dtype=DataType.VARCHAR, max_length=65535)
        ]
        if utility.has_collection(self.collection_name):
            utility.drop_collection(self.collection_name)
        
        schema = CollectionSchema(fields=fields, description="vectors with embeddings and pre-processed data")

        self.collection = Collection(name=self.collection_name, schema=schema)
        
    def embed_with_watsonx(self, inputs: Documents,client: Client, 
                parameters: Optional[TextEmbeddingParameters] = None) -> Embeddings:
        embeddings: Embeddings = []
        for response in client.text.embedding.create(
            model_id=self.tokenizer_model, inputs=inputs, parameters=parameters):
            if (len(response.results) > 0 and len(response.results[0]) > 0):
                embeddings.extend(response.results)
        return embeddings
        
    @staticmethod    
    def clean_text(text):
        # Remove unwanted characters, HTML tags, URLs, etc.
        cleaned_text = re.sub(r'<\/?[^>]*>', '', text)
        cleaned_text = re.sub(r'http\S+', '', cleaned_text)
        cleaned_text = re.sub(r'[\r\n\t]+', ' ', cleaned_text)
        return cleaned_text
    
    def tokenize_text_with_watsonx(self, documents: Documents) -> List[str]:
        """
        Tokenizes text using the genai client, handling large texts by breaking them into chunks.
        :param documents: List of text to tokenize.
        :return: The tokenization results.
        """
        results = []
        try:
            response = self.client.text.tokenization.create(
                model_id=self.tokenizer_model,
                input=documents,  # Process each chunk as a separate request
                execution_options=CreateExecutionOptions(ordered=True),
                parameters=TextTokenizationParameters(
                    return_options=TextTokenizationReturnOptions(tokens=True)
                ),
            )
            # Collect all results from the response generator
            for batch in response:
                for result in batch.results:
                    results.extend(result.tokens)  # Assuming result.tokens contains the list of tokens

        except Exception as e:
            print(f"An error occurred during tokenization: {e}")

        return results

   
    def extract_named_entities(self, text):
        # Extract named entities
        entities = self.ner_pipeline(text)
        named_entities = [(ent["entity"]) for ent in entities if ent["entity"] != "O"]
        return named_entities
    
    def perform_pos_tagging(self, text):
        pos_tags = self.pos_pipeline(text)
        return [(tag["word"], tag["entity"]) for tag in pos_tags if tag["entity"] != "O"]

    
    def perform_srl(text, tokenizer, model_name="path/to/srl/model"):
        # Load the tokenizer and model for semantic role labeling
        srl_model = ... # Load your SRL model here

        # Perform semantic role labeling
        srl_output = srl_model(text, tokenizer)

        return srl_output

    def resolve_coreferences(text, tokenizer, model_name="path/to/coref/model"):
        # Load the tokenizer and model for coreference resolution
        coref_model = ... # Load your coreference resolution model here

        # Resolve coreferences
        resolved_text = coref_model(text, tokenizer)

        return resolved_text
    
    def get_chunks(self, text):  # Helper function for chunking
        if len(text) <= CHUNK_SIZE:
            return [text]
        else:
            return [text[i:i + CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE - CHUNK_OVERLAP)]
    
    def insert_data(self):
        try: 
            with open(self.file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                embeddings, cleaned_texts = [], []

                for page in pdf_reader.pages:
                    text = page.extract_text()
                    cleaned_text = self.clean_text(text)
                    chunks = self.get_chunks(cleaned_text)

                    for chunk in chunks:
                        embedding = self.embed_with_watsonx(inputs=chunk, client=client)
                        #ids.append(len(embeddings))
                        embeddings.append(embedding)
                        cleaned_texts.append([chunk])

            # Insert data into the collection
            # iterate through the embeddings and cleaned_texts lists and create a embeddings and cleaned_text list
            for i in range(len(embeddings)):
                data_to_insert = [embeddings[i], cleaned_texts[i]]
                self.collection.insert(data_to_insert)
            
            index_params = {
                "metric_type": "L2",
                "index_type": "HNSW",
                "params": {"nlist": NLIST_SIZE},
                "M": 16,
                "efConstruction": 200,
            }
            self.collection.create_index(field_name="embeddings", index_params=index_params)
            print(len(self.collection))
        except Exception as e:
            print(f"An error occurred during data insertion: {e}")
    
    def compute_entity_match_score(self, document_entities, query_entities):
        """
        Compute the match score based on named entities.
        :param document_entities: List of entities from the document.
        :param query_entities: List of entities from the query.
        :return: Score based on the overlap of entities.
        """
        if not document_entities or not query_entities:
            return 0

        # Extract entity words from tuples
        document_entity_words = {entity[0] for entity in document_entities}
        query_entity_words = {entity[0] for entity in query_entities}

        # Calculate intersection and union for Jaccard similarity
        intersection = document_entity_words.intersection(query_entity_words)
        union = document_entity_words.union(query_entity_words)

        # Avoid division by zero
        if not union:
            return 0

        jaccard_score = len(intersection) / len(union)
        return jaccard_score

    def compute_pos_match_score(self, document_pos_tags, query_pos_tags):
        """
        Compute the match score based on POS tags.
        :param document_pos_tags: List of POS tags from the document.
        :param query_pos_tags: List of POS tags from the query.
        :return: Score based on the overlap of POS tags.
        """
        if not document_pos_tags or not query_pos_tags:
            return 0

        # Extract POS from tuples
        document_pos_set = {pos[1] for pos in document_pos_tags}
        query_pos_set = {pos[1] for pos in query_pos_tags}

        # Calculate intersection and union for Jaccard similarity
        intersection = document_pos_set.intersection(query_pos_set)
        union = document_pos_set.union(query_pos_set)

        # Avoid division by zero
        if not union:
            return 0

        jaccard_score = len(intersection) / len(union)
        return jaccard_score

    def retrieve_data(self, query_text):
        # Preprocess the query text
        cleaned_query = self.clean_text(query_text)
      
        # Generate query embedding
        query_embedding = self.embed_with_watsonx(inputs=[cleaned_query], client=client)
        
        # Perform similarity search
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
        response = self.collection.search(
            data=query_embedding, 
            anns_field="embeddings", 
            param=search_params, 
            limit=5,
            output_fields=[
                "id",
                "cleaned_text"],
            consistency_level="Strong"
            )
        
        # Filter results based on entity and POS tag matching
        results = []
        for raw_result in response:
            for document in raw_result:
                results.append(
                    RetrievedContext(
                        id=document.entity.get("id"),
                        text=document.entity.get("cleaned_text"),
                        distance=document.distance)
                )
        return results

    def prompt_template(self, context: str, question_text: str):
        return (
            f'Please answer the question using the context provided. If the question is unanswerable, say "unanswerable". Question: {question_text}.\n\n'
            + "Context:\n\n"
            + f"{context}:\n\n"
            + f'Question: {question_text}. If the question is unanswerable, say "unanswerable".'
        )

    # Token counting function
    def token_count(self, doc: str, model_id: str = "ibm/granite-13b-instruct-v2"):
        response = list(self.client.text.tokenization.create(input=[doc], model_id=model_id))
        return response[0].results[0].token_count

    def make_prompt(self, 
        relevant_documents: list[RetrievedContext],
        question_text: str,
        max_input_tokens: int,
    ):
        context = "\n\n\n".join(doc.text for doc in relevant_documents)
        prompt = self.prompt_template(context, question_text)

        prompt_token_count = self.token_count(prompt, model_id="ibm/granite-13b-instruct-v2")

        if prompt_token_count <= max_input_tokens:
            return prompt

        print("exceeded input token limit, truncating context", prompt_token_count)
        distances = [doc.distance for doc in relevant_documents]
        documents = [doc.text for doc in relevant_documents]

        # documents with the lower distance scores are included in the truncated context first
        sorted_indices = sorted(range(len(distances)), key=lambda k: distances[k])

        truncated_context = ""
        token_count_so_far = 0
        i = 0

        while token_count_so_far <= max_input_tokens and i < len(sorted_indices):
            doc_index = sorted_indices[i]
            document = documents[doc_index]
            doc_token_count = self.token_count(document)

            if token_count_so_far + doc_token_count <= max_input_tokens:
                truncated_context += document + "\n\n\n"
                token_count_so_far += doc_token_count
            else:
                remaining_tokens = max_input_tokens - token_count_so_far
                truncated_context += document[:remaining_tokens]
                break

            i += 1

        return self.prompt_template(truncated_context, question_text)

    def generate_llm_response(self, prompt: str, model_id: str = "mistralai/mistral-7b-instruct-v0-2"):
        print ("prompt", prompt)
        result = ""
        parameters = TextGenerationParameters(
            decoding_method=DecodingMethod.SAMPLE,
            max_new_tokens=500,
            min_new_tokens=5,
            temperature=0.7,
            top_k=50,
            top_p=1,
            return_options=TextGenerationReturnOptions(input_text=True),
        )
        for response in self.client.text.generation.create(
            model_id=model_id,
            input=prompt,
            parameters=parameters,
            ):
            result = response.results[0].generated_text
        return result
    
    def rag(self, question_text: str):
        # Retrieve relevant documents
        relevant_documents = self.retrieve_data(question_text)
        # Generate a prompt
        prompt = self.make_prompt(relevant_documents, "What is the ROI of AI?", 2048)
        # Generate response using LLM
        response = self.generate_llm_response(prompt)
        
        print("Question = ", question_text)
        print("Answer = ", response)
        return response

# Test code
if __name__ == "__main__":
    # Prompt the user to enter the PDF file path
    file_path = input("/Users/mg/Downloads/REPORT_Generating_ROI_with_AI.pdf")
    collection_name="test_collection"
    # Create an instance of the FileToMilvus class
    milvus_loader = FileToMilvus(collection_name="test_collection", file_path=file_path)
    if not utility.has_collection(collection_name):
        # Create a new collection
        milvus_loader.create_collection()  # Adjust the dimension as per your requirements

        # Insert data into the collection
        milvus_loader.insert_data()
    else:
        milvus_loader.collection = Collection(collection_name)
        milvus_loader.collection.load()
        
    milvus_loader.rag("What is the ROI of AI?")