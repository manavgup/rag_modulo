"""
RAG Chatbot app
======================

This is an Streamlit chatbot app with watsonx models


"""
#External libraries:
import os
import tempfile
import requests

# Third-party Libraries
import streamlit as st
from dotenv import load_dotenv
from config import CHROMA_DB_PATH

# Local/Custom Libraries
from genai.client import Client
from genai.credentials import Credentials

from ibm_watson_machine_learning.foundation_models import Model
from ibm_watson_machine_learning.metanames import GenTextModerationsMetaNames as GenParams
from ibm_watson_machine_learning.foundation_models.utils.enums import ModelTypes, DecodingMethods

from genai.extensions.langchain import LangChainInterface
from genai.schema import TextGenerationParameters, TextGenerationReturnOptions 
from langchain.vectorstores import Milvus, ElasticVectorSearch, Chroma, Pinecone
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.chains import RetrievalQA, LLMChain
from langchain.prompts import PromptTemplate
from langchain.document_loaders import Docx2txtLoader
from langchain.document_loaders import TextLoader
from langchain.document_loaders import UnstructuredMarkdownLoader
from langchain.document_loaders.csv_loader import CSVLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders import PyPDFLoader
import pinecone
import random
###Global variables:###

load_dotenv()
api_key = os.getenv("API_KEY", None)
api_endpoint = os.getenv("URL", None)
project_id = os.getenv("PROJECT_ID", None)

MILVUS_CONNECTION={"host": os.environ.get("MILVUS_HOST"), "port": os.environ.get("MILVUS_PORT")}
ELASTICSEARCH_URL=os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
MAX_HISTORY_LENGTH = 10
MIN_TEMP = float(os.environ.get("MIN_TEMPERATURE", 0.0))
MAX_TEMP = float(os.environ.get("MAX_TEMPERATURE", 2.0))
DEFAULT_TEMP = float(os.environ.get("DEFAULT_TEMPERATURE", 0.7))
MIN_MAX_TOKENS = int(os.environ.get("MIN_MAX_TOKENS", 1))
MAX_MAX_TOKENS = int(os.environ.get("MAX_MAX_TOKENS", 100000))
DEFAULT_MAX_TOKENS = int(os.environ.get("DEFAULT_MAX_TOKENS", 1000))
DEFAULT_RETRIEVER_K = 3
MIN_CHUNK_SIZE = 1
MAX_CHUNK_SIZE = 1000
DEFAULT_CHUNK_SIZE = 300
MIN_CHUNK_OVERLAP = 0
MAX_CHUNK_OVERLAP = 1000
DEFAULT_CHUNK_OVERLAP = 20
docs = []
uploaded_files = []
creds = {
    "url": api_endpoint,
    "apikey": api_key    
}

print ("creds = ", creds)
client = Client(credentials=Credentials.from_env())
suffixes = [".txt", ".md", ".pdf", ".csv", ".doc", ".docx"]
random_suffix = random.choice(suffixes)
def upload_file():
    uploaded_files = st.sidebar.file_uploader(
        'Browse file',
         type=['pdf', 'txt', 'md', 'doc', 'docx', 'csv'],
         accept_multiple_files=True)
    return uploaded_files

def connect(connection_info,index_name):
    index = Milvus(
           EMBED,
           connection_args=connection_info,
           collection_name=index_name,
           index_params="text"
       )
    return index

def clear_chat_history():
    st.session_state.messages = [{"role": "assistant", "content": "How may I assist you today?"}]

def index_with_chroma(docs, EMBED, index_name):
    chroma_db = Chroma.from_documents(docs, EMBED, collection_name=index_name, persist_directory=CHROMA_DB_PATH)
    chroma_db.persist()

def index_with_milvus(docs, EMBED, index_name):
    Milvus.from_documents(documents=docs, embedding=EMBED, connection_args=MILVUS_CONNECTION, collection_name=index_name)

def index_with_pinecone(docs, EMBED, index_name, DIMENSIONS):
    pinecone.init(
        api_key=os.environ["PINECONE_API_KEY"],
        environment=os.environ["PINECONE_ENVIRONMENT"],
        )
    indexes = pinecone.list_indexes()
    for i in indexes:
        print('Deleting all indexes ... ', end='')
        pinecone.delete_index(i)
    if index_name not in pinecone.list_indexes():
       print(f'Creating index {index_name} ...')
       pinecone.create_index(index_name, dimension=DIMENSIONS, metric='cosine')
       print('Create Index Done!')
       Pinecone.from_documents(docs, EMBED, index_name=index_name)

def index_with_elasticsearch(docs, EMBED, index_name):
    db = ElasticVectorSearch.from_documents(
        docs,
        EMBED,
        elasticsearch_url=ELASTICSEARCH_URL,
        index_name=index_name,
    )
    print(db.client.info())


def index_documents( uploaded_files,selected_option, selected_embedding,chunk_size,chunk_overlap,index_name):
    # Your indexing logic here
    documents = []
    for uploaded_file in uploaded_files:
            filename = os.path.basename(uploaded_file.name)
            suffix = os.path.splitext(filename)[1].lower()
            file_bytes = uploaded_file.read()
            with tempfile.NamedTemporaryFile(delete=False, suffix=random_suffix) as temp_file:
                temp_file.write(file_bytes)
                temp_file_path = temp_file.name
                if suffix == '.pdf':
                    loader = PyPDFLoader(temp_file_path)
                    documents.extend(loader.load())
                if suffix == '.txt':
                    loader = TextLoader(temp_file_path)
                    documents.extend(loader.load())
                if suffix == '.md':
                    loader =  UnstructuredMarkdownLoader(temp_file_path)  
                    documents.extend(loader.load())  
                if suffix == '.csv':
                    loader =  CSVLoader(temp_file_path)     
                    documents.extend(loader.load())
                if suffix == '.docx':
                    loader =  Docx2txtLoader(temp_file_path) 
                    documents.extend(loader.load())    
                text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_size,separators=["\n"])
                docs = text_splitter.split_documents(documents)   
    ids = [str(i) for i in list(range(1, len(docs) + 1))]
    EMBED = HuggingFaceEmbeddings(model_name=selected_embedding)
    EMBEDDING_DIMENSIONS = {
    'sentence-transformers/all-MiniLM-L6-v2': 384,
    'sentence-transformers/all-mpnet-base-v2': 768, 
    'BAAI/bge-large-en-v1.5': 1024,
    'BAAI/bge-base-en-v1.5': 768,
    'BAAI/bge-small-en-v1.5': 384,
    'thenlper/gte-base': 768
    }

    DIMENSIONS = 384  

    if selected_embedding in EMBEDDING_DIMENSIONS:
     DIMENSIONS = EMBEDDING_DIMENSIONS[selected_embedding] 
    
    if selected_option == 'chroma':
        index_with_chroma(docs, EMBED, index_name)
    elif selected_option == 'milvus':
        index_with_milvus(docs, EMBED, index_name)
    elif selected_option == 'pinecone':
        index_with_pinecone(docs, EMBED, index_name,DIMENSIONS)
    elif selected_option == 'elasticsearch':
        index_with_elasticsearch(docs, EMBED, index_name)
    
    print(f"Indexed {len(ids)} documents")
    st.sidebar.success('Documents indexed successfully!')

###Initial UI configuration:###
st.set_page_config(page_title="RAG Demo by IBM", page_icon="🦙", layout="wide")
st.write(f"streamlit version: {st.__version__}")


def render_app():

    # reduce font sizes for input text boxes
    custom_css = """
        <style>
            .stTextArea textarea {font-size: 13px;}
            div[data-baseweb="select"] > div {font-size: 13px !important;}
        </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)


    #Set config for a cleaner menu, footer & background:
    hide_streamlit_style = """
                <style>
                #MainMenu {visibility: hidden;}
                footer {visibility: hidden;}
                </style>
                """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)

    #container for the chat history
    response_container = st.container()
    #container for the user's text input
    container = st.container()
    #Set up/Initialize Session State variables:
    if 'chat_dialogue' not in st.session_state:
        st.session_state['chat_dialogue'] = []
    
    if 'string_dialogue' not in st.session_state:
        st.session_state['string_dialogue'] = ''

def get_model_ids(api_url=api_endpoint, api_key=api_key):
    models = []
    for model in ModelTypes:
        # model = Model(model_id=model, credentials=creds, params=None, project_id=project_id)
        print (f"model={model}, ${model.value}")
        models.append(model.value)

    return models

if 'modelids' not in st.session_state:
    st.session_state['modelids'] = []

# Check if st.session_state['modelid'] is empty
if not st.session_state['modelids']:
    # If empty, fetch the model IDs and store in the session state
    st.session_state['modelids'] = get_model_ids()

# Return the value (either the pre-existing value or the freshly fetched one)
model_ids = st.session_state['modelids']


with st.sidebar:
    model = st.selectbox(label="Model", options=model_ids, index=model_ids.index("google/flan-ul2"))  
    st.session_state['llm'] = model 
   
    selected_option = st.sidebar.selectbox('Choose a vector store', ['chroma','milvus','pinecone','elasticsearch' ], key='vectordb')
    selected_embedding = st.sidebar.selectbox('Choose embedding', ['sentence-transformers/all-MiniLM-L6-v2','sentence-transformers/all-mpnet-base-v2','BAAI/bge-large-en-v1.5','BAAI/bge-base-en-v1.5','BAAI/bge-small-en-v1.5','thenlper/gte-base' ])
    uploaded_filess =upload_file()
    print(f'Total documents after split: {len(uploaded_filess)}')


with st.sidebar.expander("Advanced Options", expanded=False):
        
        temperature = st.slider(
            label="Temperature",
            min_value=MIN_TEMP,
            max_value=MAX_TEMP,
            value=DEFAULT_TEMP,
            help="Higher values give more random results.",
        )

        k = st.slider(
            label="Top k",
            help="How many document chunks will be used for context?",
            value=DEFAULT_RETRIEVER_K,
            min_value=1,
            max_value=10,
        )

        chunk_size = st.slider(
            label="Number of Tokens per Chunk",
            help="Size of each chunk of text",
            min_value=MIN_CHUNK_SIZE,
            max_value=MAX_CHUNK_SIZE,
            value=DEFAULT_CHUNK_SIZE,
        )

        chunk_overlap = st.slider(
            label="Chunk Overlap",
            help="Number of characters to overlap between chunks",
            min_value=MIN_CHUNK_OVERLAP,
            max_value=MAX_CHUNK_OVERLAP,
            value=DEFAULT_CHUNK_OVERLAP,
        ) 

        index_name =  st.text_input(
            "Index name",
            value='demo'
        )

        document_chat = st.checkbox(
            "Document Chat",
            value=True,
            help="Uploaded document will provide context for the chat.",
        )

        chain_type_help_root = (
            "https://python.langchain.com/docs/modules/chains/document/"
        )
        chain_type_help = "\n".join(
            f"- [{chain_type_name}]({chain_type_help_root}/{chain_type_name})"
            for chain_type_name in (
                "stuff",
                "refine",
                "map_reduce",
                "map_rerank",
            )
        )
        document_chat_chain_type = st.selectbox(
            label="Document Chat Chain Type",
            options=[
                "stuff",
                "refine",
                "map_reduce",
                "map_rerank"
            ],
            index=0,
            help=chain_type_help,
            disabled=not document_chat,
        )
        
        show_sources = st.toggle("Show Sources", False) 
        

# Add process button
if st.sidebar.button('Index Documents'):
    if (len(uploaded_filess)>0):
       index_documents(uploaded_filess,selected_option, selected_embedding, chunk_size, chunk_overlap,index_name)

st.sidebar.button('Clear Chat History', on_click=clear_chat_history)
st.sidebar.write(" ")
params = TextGenerationParameters(decoding_method=DecodingMethods.GREEDY,
                                max_new_tokens=1536,
                                min_new_tokens=1,
                                temperature=temperature,
                                repetition_penalty=1)
# Accept user input
if "messages" not in st.session_state.keys():
    st.session_state.messages = [{"role": "assistant", "content": "How may I assist you today?"}]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if prompt := st.chat_input("Type your question here..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

if st.session_state.messages[-1]["role"] != "assistant":
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
             llm = LangChainInterface(model=st.session_state['llm'], params=params, credentials=creds)
             EMBED = HuggingFaceEmbeddings(model_name=selected_embedding)
             if not document_chat:
               template = """Question: {question} """
               promptTemplate = PromptTemplate(template=template, input_variables=["question"])
               llm_chain = LLMChain(prompt=promptTemplate, llm=llm)
               llm_chain.run(prompt)
               template = """
               You are a friendly chatbot assistant that responds in a conversational
               manner to users questions. Keep the answers short, unless specifically
               asked by the user to elaborate on something.

               Question: {question}

               Answer:"""
               promptTemplate = PromptTemplate(template=template, input_variables=["question"])

               llm_chain = LLMChain(prompt=promptTemplate, llm=llm)
               full_response=llm_chain.run(prompt) 
               placeholder = st.empty()
               placeholder.markdown(full_response)
             else:
                full_response = ''
                if (selected_option  =='chroma'):
                    chroma_db = Chroma(persist_directory=CHROMA_DB_PATH, embedding_function=EMBED, collection_name=index_name)
                    print ("chroma = ", chroma_db)
                    qa = RetrievalQA.from_chain_type(llm=llm, 
                                    chain_type=document_chat_chain_type, 
                                    retriever=chroma_db.as_retriever(search_kwargs={"k": k}), 
                                    return_source_documents=True
                                    )
                    res = qa(prompt)  
                    full_response = res["result"].replace("<|endoftext|>", "")
                if (selected_option  =='milvus'):
                    vectordb = connect(MILVUS_CONNECTION,index_name)
                    qa = RetrievalQA.from_chain_type(llm=llm, 
                                    chain_type=document_chat_chain_type, 
                                    retriever=vectordb.as_retriever(search_kwargs={"k": k}), 
                                    return_source_documents=True
                                    )
                    res = qa(prompt)  
                    full_response = res["result"].replace("<|endoftext|>", "")
                if (selected_option  =='pinecone'):
                     pinecone.init(
                        api_key=os.environ["PINECONE_API_KEY"],
                        environment=os.environ["PINECONE_ENVIRONMENT"],
                     )
                     pc_index = pinecone.Index(index_name)
                     print(pc_index.describe_index_stats())      
                     vectordb = Pinecone.from_existing_index(
                     embedding=EMBED,
                     index_name=index_name,
                     )
                     qa = RetrievalQA.from_chain_type(llm=llm, 
                                    chain_type=document_chat_chain_type, 
                                    retriever=vectordb.as_retriever(search_kwargs={"k": k}), 
                                    return_source_documents=True
                                    )
                     res = qa(prompt)  
                     full_response = res["result"].replace("<|endoftext|>", "")
                if (selected_option  =='elasticsearch'):
                    elasticdb = ElasticVectorSearch(
                    elasticsearch_url=ELASTICSEARCH_URL,
                    index_name=index_name,
                    embedding=EMBED ,
                    )
                    qa = RetrievalQA.from_chain_type(llm=llm, 
                                    chain_type=document_chat_chain_type, 
                                    retriever=elasticdb.as_retriever(search_kwargs={"k": k}), 
                                    return_source_documents=True
                                    )
                    res = qa(prompt)  
                    full_response = res["result"].replace("<|endoftext|>", "")
                placeholder = st.empty()
                placeholder.markdown(full_response)           
                if show_sources:
                    st.write("Answer Sources")
                    st.write(res)
    message = {"role": "assistant", "content": full_response}
    st.session_state.messages.append(message)          
   

render_app()
