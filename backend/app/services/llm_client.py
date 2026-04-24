import os
import json
from typing import List, Optional, Dict, Any, Generator
import httpx


class LLMClient:
    """Unified LLM client supporting OpenAI, Anthropic, and Ollama."""
    
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "ollama").lower()
        self.default_model = os.getenv("LLM_MODEL", "qwen2.5:7b")
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))
        self.top_p = float(os.getenv("LLM_TOP_P", "0.9"))
        
        # OpenAI config
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        
        # Anthropic config
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        
        # Ollama config
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
        self.ollama_embed_model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """Get list of available models based on provider."""
        if self.provider == "openai" and self.openai_api_key:
            return [
                {"id": "gpt-4o", "name": "GPT-4o", "provider": "openai"},
                {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "provider": "openai"},
                {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "provider": "openai"},
                {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "provider": "openai"},
            ]
        elif self.provider == "anthropic" and self.anthropic_api_key:
            return [
                {"id": "claude-sonnet-4-20250514", "name": "Claude Sonnet 4", "provider": "anthropic"},
                {"id": "claude-opus-4-20250514", "name": "Claude Opus 4", "provider": "anthropic"},
                {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus", "provider": "anthropic"},
                {"id": "claude-3-sonnet-20240229", "name": "Claude 3 Sonnet", "provider": "anthropic"},
            ]
        else:
            # Return Ollama models
            return self._get_ollama_models()
    
    def _get_ollama_models(self) -> List[Dict[str, Any]]:
        """Get list of Ollama models."""
        try:
            url = f"{self.ollama_base_url}/api/tags"
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    return [
                        {"id": m.get("name", ""), "name": m.get("name", ""), "provider": "ollama"}
                        for m in data.get("models", [])
                    ]
        except Exception:
            pass
        return [{"id": "qwen2.5:7b", "name": "Qwen 2.5 7B", "provider": "ollama"}]
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        stream: bool = False
    ) -> str:
        """Send chat request to LLM provider."""
        model = model or self.default_model
        temp = temperature or self.temperature
        
        if self.provider == "openai" or (self.provider == "auto" and self.openai_api_key):
            return await self._openai_chat(messages, model, temp, stream)
        elif self.provider == "anthropic" or (self.provider == "auto" and self.anthropic_api_key):
            return await self._anthropic_chat(messages, model, temp, stream)
        else:
            return await self._ollama_chat(messages, model, temp, stream)
    
    async def _openai_chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        stream: bool
    ) -> str:
        """OpenAI API chat."""
        url = f"{self.openai_base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        if "gpt" in model and "-3.5" not in model and "-4" not in model:
            model = "gpt-4o"
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": self.top_p,
            "stream": stream
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if stream:
                return data  # Return full response for streaming
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    
    async def _anthropic_chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        stream: bool
    ) -> str:
        """Anthropic API chat."""
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        
        # Map model names
        model_map = {
            "claude-sonnet-4-20250514": "claude-sonnet-4-20250514",
            "claude-opus-4-20250514": "claude-opus-4-20250514",
            "claude-3-opus-20240229": "claude-3-opus-20240229",
            "claude-3-sonnet-20240229": "claude-3-sonnet-20240229",
        }
        anthropic_model = model_map.get(model, "claude-sonnet-4-20250514")
        
        # Convert messages format
        system_message = ""
        anthropic_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_message = msg.get("content", "")
            else:
                anthropic_messages.append(msg)
        
        payload = {
            "model": anthropic_model,
            "max_tokens": 4096,
            "messages": anthropic_messages,
            "temperature": temperature,
            "top_p": self.top_p,
            "system": system_message
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data.get("content", [{}])[0].get("text", "")
    
    async def _ollama_chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        stream: bool
    ) -> str:
        """Ollama API chat."""
        url = f"{self.ollama_base_url}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "top_p": self.top_p
            }
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")
    
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> Generator[str, None, None]:
        """Send chat request with streaming response."""
        model = model or self.default_model
        temp = temperature or self.temperature
        
        if self.provider == "openai" or (self.provider == "auto" and self.openai_api_key):
            async for chunk in self._openai_stream(messages, model, temp):
                yield chunk
        elif self.provider == "anthropic" or (self.provider == "auto" and self.anthropic_api_key):
            async for chunk in self._anthropic_stream(messages, model, temp):
                yield chunk
        else:
            async for chunk in self._ollama_stream(messages, model, temp):
                yield chunk
    
    async def _openai_stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float
    ) -> Generator[str, None, None]:
        """OpenAI streaming chat."""
        url = f"{self.openai_base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": True
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "choices" in data:
                                content = data["choices"][0].get("delta", {}).get("content")
                                if content:
                                    yield content
                        except:
                            pass
    
    async def _anthropic_stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float
    ) -> Generator[str, None, None]:
        """Anthropic streaming chat."""
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        
        model_map = {
            "claude-sonnet-4-20250514": "claude-sonnet-4-20250514",
            "claude-opus-4-20250514": "claude-opus-4-20250514",
        }
        anthropic_model = model_map.get(model, "claude-sonnet-4-20250514")
        
        system_message = ""
        anthropic_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_message = msg.get("content", "")
            else:
                anthropic_messages.append(msg)
        
        payload = {
            "model": anthropic_model,
            "max_tokens": 4096,
            "messages": anthropic_messages,
            "temperature": temperature,
            "stream": True,
            "system": system_message
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "delta" in data:
                                content = data["delta"].get("text")
                                if content:
                                    yield content
                        except:
                            pass
    
    async def _ollama_stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float
    ) -> Generator[str, None, None]:
        """Ollama streaming chat."""
        url = f"{self.ollama_base_url}/api/chat"
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature
            }
        }
        
        full_response = []
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                content = data["message"]["content"]
                                yield content
                        except:
                            pass
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate text embedding."""
        # Use OpenAI embeddings if available
        if self.openai_api_key and self.provider != "ollama":
            return await self._openai_embedding(text)
        
        # Use Ollama embeddings as fallback
        try:
            return await self._ollama_embedding(text)
        except:
            # Return zero vector if no embeddings available
            return [0.0] * 768
    
    async def _openai_embedding(self, text: str) -> List[float]:
        """OpenAI text embeddings."""
        url = f"{self.openai_base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "text-embedding-3-small",
            "input": text
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [{}])[0].get("embedding", [])
    
    async def _ollama_embedding(self, text: str) -> List[float]:
        """Ollama text embeddings."""
        url = f"{self.ollama_base_url}/api/embeddings"
        payload = {
            "model": self.ollama_embed_model,
            "prompt": text
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("embedding", [])
    
    def test_connection(self) -> Dict[str, Any]:
        """Test LLM provider connection."""
        try:
            models = self.get_available_models()
            return {
                "success": True,
                "provider": self.provider,
                "models": models,
                "default_model": self.default_model
            }
        except Exception as e:
            return {
                "success": False,
                "provider": self.provider,
                "error": str(e)
            }


# Singleton instance
llm_client = LLMClient()