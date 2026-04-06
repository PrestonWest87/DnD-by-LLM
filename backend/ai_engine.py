import os
import httpx
from chromadb.config import Settings
import chromadb

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
MODEL_NAME = "phi4-mini:3.8b-q4_K_M"

class LocalOllamaEmbeddingFunction:
    def __call__(self, input: list[str]) -> list[list[float]]:
        embeddings = []
        with httpx.Client() as client:
            for text in input:
                res = client.post(f"{OLLAMA_URL}/api/embeddings", json={"model": "nomic-embed-text", "prompt": text}, timeout=60.0)
                embeddings.append(res.json()["embedding"])
        return embeddings

# Persist to data volume
chroma_client = chromadb.PersistentClient(path="./data/chroma", settings=Settings(anonymized_telemetry=False))
rules_collection = chroma_client.get_or_create_collection(name="ttrpg_rules", embedding_function=LocalOllamaEmbeddingFunction())

def retrieve_relevant_rules(query: str, n_results: int = 2) -> str:
    # Safeguard: Do not query if empty
    if rules_collection.count() == 0:
        return "No specific rules loaded."
    results = rules_collection.query(query_texts=[query], n_results=n_results)
    if not results['documents'] or not results['documents'][0]: return ""
    return "\n".join(results['documents'][0])

async def generate_ai_response(system_prompt: str, messages: list) -> str:
    payload = [{"role": "system", "content": system_prompt}] + messages
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{OLLAMA_URL}/api/chat", json={"model": MODEL_NAME, "messages": payload, "stream": False}, timeout=90.0)
            response.raise_for_status()
            return response.json().get("message", {}).get("content", "...")
        except Exception as e:
            return f"System Error: ({str(e)})"
