"""
LLM Router — Multi-provider abstraction layer
Supports: OpenAI, Anthropic, Google, Ollama
"""
from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class Message:
    role: str  # system, user, assistant
    content: str


@dataclass
class ChatResponse:
    content: str
    model: str
    provider: str
    tokens_used: int = 0
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EmbeddingResponse:
    embedding: List[float]
    model: str
    provider: str
    dimensions: int = 0


class LLMProvider(ABC):
    """Base class for LLM providers"""

    @abstractmethod
    async def chat(self, messages: List[Message], **kwargs) -> ChatResponse:
        pass

    @abstractmethod
    async def embed(self, text: str) -> EmbeddingResponse:
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[EmbeddingResponse]:
        pass


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini",
                 embedding_model: str = "text-embedding-3-small"):
        self.api_key = api_key
        self.model = model
        self.embedding_model = embedding_model
        self.base_url = "https://api.openai.com/v1"
        self.client = httpx.AsyncClient(timeout=60.0)

    async def chat(self, messages: List[Message], **kwargs) -> ChatResponse:
        resp = await self.client.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": kwargs.get("model", self.model),
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                "temperature": kwargs.get("temperature", 0.7),
                "max_tokens": kwargs.get("max_tokens", 2000),
            },
        )
        resp.raise_for_status()
        data = resp.json()
        usage = data.get("usage", {})
        return ChatResponse(
            content=data["choices"][0]["message"]["content"],
            model=data.get("model", self.model),
            provider="openai",
            tokens_used=usage.get("total_tokens", 0),
            raw=data,
        )

    async def embed(self, text: str) -> EmbeddingResponse:
        results = await self.embed_batch([text])
        return results[0]

    async def embed_batch(self, texts: List[str]) -> List[EmbeddingResponse]:
        resp = await self.client.post(
            f"{self.base_url}/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.embedding_model, "input": texts},
        )
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data["data"]:
            emb = item["embedding"]
            results.append(EmbeddingResponse(
                embedding=emb,
                model=self.embedding_model,
                provider="openai",
                dimensions=len(emb),
            ))
        return results


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514",
                 embedding_provider: Optional[LLMProvider] = None):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.anthropic.com/v1"
        self.client = httpx.AsyncClient(timeout=60.0)
        # Anthropic doesn't have embeddings → fallback to another provider
        self._embedding_fallback = embedding_provider

    async def chat(self, messages: List[Message], **kwargs) -> ChatResponse:
        # Separate system message
        system_msg = None
        chat_msgs = []
        for m in messages:
            if m.role == "system":
                system_msg = m.content
            else:
                chat_msgs.append({"role": m.role, "content": m.content})

        body: Dict[str, Any] = {
            "model": kwargs.get("model", self.model),
            "messages": chat_msgs,
            "max_tokens": kwargs.get("max_tokens", 2000),
        }
        if system_msg:
            body["system"] = system_msg

        resp = await self.client.post(
            f"{self.base_url}/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()
        usage = data.get("usage", {})
        content_blocks = data.get("content", [])
        text = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")

        return ChatResponse(
            content=text,
            model=data.get("model", self.model),
            provider="anthropic",
            tokens_used=usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            raw=data,
        )

    async def embed(self, text: str) -> EmbeddingResponse:
        if self._embedding_fallback:
            return await self._embedding_fallback.embed(text)
        raise NotImplementedError("Anthropic does not support embeddings. Set EMBEDDING_PROVIDER.")

    async def embed_batch(self, texts: List[str]) -> List[EmbeddingResponse]:
        if self._embedding_fallback:
            return await self._embedding_fallback.embed_batch(texts)
        raise NotImplementedError("Anthropic does not support embeddings. Set EMBEDDING_PROVIDER.")


class GoogleProvider(LLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash",
                 embedding_model: str = "text-embedding-004"):
        self.api_key = api_key
        self.model = model
        self.embedding_model = embedding_model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.client = httpx.AsyncClient(timeout=60.0)

    async def chat(self, messages: List[Message], **kwargs) -> ChatResponse:
        # Convert to Gemini format
        system_instruction = None
        contents = []
        for m in messages:
            if m.role == "system":
                system_instruction = m.content
            else:
                role = "user" if m.role == "user" else "model"
                contents.append({"role": role, "parts": [{"text": m.content}]})

        body: Dict[str, Any] = {"contents": contents}
        if system_instruction:
            body["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        model = kwargs.get("model", self.model)
        resp = await self.client.post(
            f"{self.base_url}/models/{model}:generateContent?key={self.api_key}",
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()
        text = ""
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts)

        usage = data.get("usageMetadata", {})
        return ChatResponse(
            content=text,
            model=model,
            provider="google",
            tokens_used=usage.get("totalTokenCount", 0),
            raw=data,
        )

    async def embed(self, text: str) -> EmbeddingResponse:
        results = await self.embed_batch([text])
        return results[0]

    async def embed_batch(self, texts: List[str]) -> List[EmbeddingResponse]:
        # Google batches via single request with multiple texts
        results = []
        for text in texts:
            resp = await self.client.post(
                f"{self.base_url}/models/{self.embedding_model}:embedContent?key={self.api_key}",
                json={"model": f"models/{self.embedding_model}",
                      "content": {"parts": [{"text": text}]}},
            )
            resp.raise_for_status()
            data = resp.json()
            emb = data["embedding"]["values"]
            results.append(EmbeddingResponse(
                embedding=emb, model=self.embedding_model,
                provider="google", dimensions=len(emb),
            ))
        return results


class OllamaProvider(LLMProvider):
    def __init__(self, base_url: str = "http://localhost:11434",
                 model: str = "llama3.2", embedding_model: str = "nomic-embed-text"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.embedding_model = embedding_model
        self.client = httpx.AsyncClient(timeout=120.0)

    async def chat(self, messages: List[Message], **kwargs) -> ChatResponse:
        resp = await self.client.post(
            f"{self.base_url}/api/chat",
            json={
                "model": kwargs.get("model", self.model),
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                "stream": False,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return ChatResponse(
            content=data.get("message", {}).get("content", ""),
            model=data.get("model", self.model),
            provider="ollama",
            tokens_used=data.get("eval_count", 0) + data.get("prompt_eval_count", 0),
            raw=data,
        )

    async def embed(self, text: str) -> EmbeddingResponse:
        resp = await self.client.post(
            f"{self.base_url}/api/embed",
            json={"model": self.embedding_model, "input": text},
        )
        resp.raise_for_status()
        data = resp.json()
        embs = data.get("embeddings", [[]])[0]
        return EmbeddingResponse(
            embedding=embs, model=self.embedding_model,
            provider="ollama", dimensions=len(embs),
        )

    async def embed_batch(self, texts: List[str]) -> List[EmbeddingResponse]:
        results = []
        for text in texts:
            results.append(await self.embed(text))
        return results


# ─── Embedding dimension lookup ─────────────────────────

EMBEDDING_DIMS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
    "text-embedding-004": 768,
    "nomic-embed-text": 768,
}


# ─── Router (main entry point) ──────────────────────────

class LLMRouter:
    """
    Multi-provider LLM router with automatic fallback.

    Usage:
        router = LLMRouter.from_env()
        response = await router.chat([Message("user", "Hello")])
        embedding = await router.embed("Some text")
    """

    def __init__(self, primary: LLMProvider, fallback: Optional[LLMProvider] = None):
        self.primary = primary
        self.fallback = fallback

    @classmethod
    def from_env(cls) -> "LLMRouter":
        """Create router from environment variables."""
        provider = os.getenv("LLM_PROVIDER", "openai").lower()
        api_key = os.getenv("LLM_API_KEY", "")
        model = os.getenv("LLM_MODEL", "")
        emb_provider = os.getenv("EMBEDDING_PROVIDER", provider).lower()
        emb_model = os.getenv("EMBEDDING_MODEL", "")

        # Build embedding provider first (for Anthropic fallback)
        embedding_llm = None
        if emb_provider != provider:
            emb_key = os.getenv("EMBEDDING_API_KEY", api_key)
            embedding_llm = cls._build_provider(emb_provider, emb_key, "", emb_model)

        primary = cls._build_provider(provider, api_key, model, emb_model, embedding_llm)

        # Fallback
        fb_provider_name = os.getenv("LLM_FALLBACK_PROVIDER", "").lower()
        fallback = None
        if fb_provider_name:
            fb_key = os.getenv("LLM_FALLBACK_API_KEY", "")
            fb_model = os.getenv("LLM_FALLBACK_MODEL", "")
            fallback = cls._build_provider(fb_provider_name, fb_key, fb_model, emb_model)

        return cls(primary=primary, fallback=fallback)

    @staticmethod
    def _build_provider(name: str, api_key: str, model: str, emb_model: str,
                        embedding_fallback: Optional[LLMProvider] = None) -> LLMProvider:
        if name == "openai":
            return OpenAIProvider(
                api_key=api_key,
                model=model or "gpt-4o-mini",
                embedding_model=emb_model or "text-embedding-3-small",
            )
        elif name == "anthropic":
            return AnthropicProvider(
                api_key=api_key,
                model=model or "claude-sonnet-4-20250514",
                embedding_provider=embedding_fallback,
            )
        elif name == "google":
            return GoogleProvider(
                api_key=api_key,
                model=model or "gemini-2.0-flash",
                embedding_model=emb_model or "text-embedding-004",
            )
        elif name == "ollama":
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            return OllamaProvider(
                base_url=base_url,
                model=model or "llama3.2",
                embedding_model=emb_model or "nomic-embed-text",
            )
        else:
            raise ValueError(f"Unknown LLM provider: {name}")

    async def chat(self, messages: List[Message], **kwargs) -> ChatResponse:
        try:
            return await self.primary.chat(messages, **kwargs)
        except Exception as e:
            if self.fallback:
                logger.warning(f"Primary provider failed ({e}), falling back")
                return await self.fallback.chat(messages, **kwargs)
            raise

    async def embed(self, text: str) -> EmbeddingResponse:
        try:
            return await self.primary.embed(text)
        except Exception as e:
            if self.fallback:
                logger.warning(f"Primary embedding failed ({e}), falling back")
                return await self.fallback.embed(text)
            raise

    async def embed_batch(self, texts: List[str]) -> List[EmbeddingResponse]:
        try:
            return await self.primary.embed_batch(texts)
        except Exception as e:
            if self.fallback:
                logger.warning(f"Primary batch embedding failed ({e}), falling back")
                return await self.fallback.embed_batch(texts)
            raise

    def get_embedding_dim(self) -> int:
        """Get expected embedding dimensions for the configured model."""
        emb_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        return EMBEDDING_DIMS.get(emb_model, 1536)
