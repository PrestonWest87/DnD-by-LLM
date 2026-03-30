import chromadb
import httpx
import os

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

# --- Custom Embedding Function ---
class LocalOllamaEmbeddingFunction:
    """Custom embedder to bypass version limitations in ChromaDB"""
    def __init__(self, url: str, model_name: str):
        self.url = url
        self.model_name = model_name

    def __call__(self, input: list[str]) -> list[list[float]]:
        embeddings = []
        with httpx.Client() as client:
            for text in input:
                response = client.post(
                    f"{self.url}/api/embeddings",
                    json={"model": self.model_name, "prompt": text},
                    timeout=60.0
                )
                response.raise_for_status()
                embeddings.append(response.json()["embedding"])
        return embeddings

# Configure Chroma to use our custom Ollama embedder
ollama_ef = LocalOllamaEmbeddingFunction(
    url=OLLAMA_URL,
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
    A simple chunker. Splits by double-newlines (paragraphs/sections) to keep it lightweight.
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
