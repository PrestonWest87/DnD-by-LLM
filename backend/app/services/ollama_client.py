import os
import json
from typing import List, Optional, Dict, Any
import httpx


class OllamaClient:
    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
        self.embed_model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
        self.chat_model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        stream: bool = False
    ) -> str:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model or self.chat_model,
            "messages": messages,
            "stream": stream
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None
    ) -> List[str]:
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model or self.chat_model,
            "messages": messages,
            "stream": True
        }

        full_response = []
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            content = data["message"]["content"]
                            full_response.append(content)
        
        return full_response

    async def generate_embedding(self, text: str) -> List[float]:
        url = f"{self.base_url}/api/embeddings"
        payload = {
            "model": self.embed_model,
            "prompt": text
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("embedding", [])

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        stream: bool = False
    ) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": model or self.chat_model,
            "prompt": prompt,
            "stream": stream
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")

    async def list_models(self) -> List[str]:
        url = f"{self.base_url}/api/tags"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            return [m.get("name", "") for m in data.get("models", [])]