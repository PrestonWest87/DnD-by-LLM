import chromadb
from chromadb.utils import embedding_functions
import os

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

# Configure Chroma to use Ollama for creating embeddings
ollama_ef = embedding_functions.OllamaEmbeddingFunction(
    url=f"{OLLAMA_URL}/api/embeddings",
    model_name="nomic-embed-text"
)

# Initialize a persistent local vector database
chroma_client = chromadb.PersistentClient(path="./chroma_data")

# Get or create the collection that will hold our rulebook
rules_collection = chroma_client.get_or_create_collection(
    name="ttrpg_rules",
    embedding_function=ollama_ef
)

def ingest_rulebook(text_content: str):
    """
    A simple chunker. In a production app, you'd use LangChain's RecursiveCharacterTextSplitter.
    Here, we split by double-newlines (paragraphs/sections) to keep it lightweight.
    """
    chunks = [chunk.strip() for chunk in text_content.split("\n\n") if len(chunk.strip()) > 50]
    
    ids = [f"rule_chunk_{i}" for i in range(len(chunks))]
    
    # Upsert clears out old chunks with the same ID and adds the new ones
    rules_collection.upsert(
        documents=chunks,
        ids=ids
    )
    return len(chunks)

def retrieve_relevant_rules(query: str, n_results: int = 2) -> str:
    """
    Searches the vector database for rules related to the player's action.
    """
    results = rules_collection.query(
        query_texts=[query],
        n_results=n_results
    )
    
    if not results['documents'] or not results['documents'][0]:
        return ""
    
    # Combine the top results into a single string
    return "\n".join(results['documents'][0])
