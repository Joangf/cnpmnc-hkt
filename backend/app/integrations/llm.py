"""Thin client for the OpenAI-compatible AI gateway (LiteLLM): chat, dense and ColBERT embeddings.

Every failure surfaces as `AIUnavailable`, so callers have one thing to catch before
falling back to rule-only behaviour. Chat tokens are counted per clinic day in Redis and
refused above `llm_daily_token_budget` (the key is paid for by the team).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx
import numpy as np
import structlog

from app.core.config import settings
from app.core.redis import redis_client

logger = structlog.get_logger(__name__)


class AIUnavailable(Exception):
    """The gateway is off, failing, slow, over budget, or returned something unusable."""


class BudgetExceeded(AIUnavailable):
    pass


def _budget_key() -> str:
    return f"llm:tokens:{datetime.now(ZoneInfo(settings.clinic_timezone)).date().isoformat()}"


class LLMClient:
    def __init__(self, base_url: str, api_key: str, timeout: float) -> None:
        self._http = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        try:
            response = await self._http.post(path, json=body)
        except httpx.HTTPError as exc:
            raise AIUnavailable(f"{path}: {type(exc).__name__}") from exc
        if response.status_code >= 400:
            raise AIUnavailable(f"{path}: HTTP {response.status_code} {response.text[:200]}")
        try:
            return response.json()
        except ValueError as exc:
            raise AIUnavailable(f"{path}: invalid JSON") from exc

    async def tokens_used_today(self) -> int:
        return int(await redis_client.get(_budget_key()) or 0)

    async def chat(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int,
        temperature: float = 0.2,
        json_output: bool = False,
        purpose: str,
    ) -> str:
        budget = settings.llm_daily_token_budget
        if budget and await self.tokens_used_today() >= budget:
            raise BudgetExceeded("daily LLM token budget reached")
        body: dict[str, Any] = {
            "model": settings.llm_model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if settings.llm_disable_thinking:
            body["thinking"] = {"type": "disabled"}
        if json_output:
            body["response_format"] = {"type": "json_object"}
        data = await self._post("/chat/completions", body)
        usage = data.get("usage") or {}
        total = int(usage.get("total_tokens") or 0)
        if total:
            key = _budget_key()
            await redis_client.incrby(key, total)
            await redis_client.expire(key, 2 * 24 * 3600)
        logger.info("llm_chat", purpose=purpose, tokens=total, model=settings.llm_model)
        try:
            content = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise AIUnavailable("chat: no content") from exc
        return content.strip()

    async def chat_json(self, system: str, user: str, *, max_tokens: int, purpose: str) -> Any:
        text = await self.chat(
            system, user, max_tokens=max_tokens, json_output=True, purpose=purpose
        )
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            return json.loads(text)
        except ValueError as exc:
            raise AIUnavailable(f"{purpose}: model did not return JSON") from exc

    async def embed(self, texts: list[str]) -> list[np.ndarray]:
        """Dense vectors, L2-normalised, one per input in input order."""
        data = await self._post("/embeddings", {"model": settings.embedding_model, "input": texts})
        rows = sorted(data.get("data") or [], key=lambda r: r.get("index", 0))
        if len(rows) != len(texts):
            raise AIUnavailable("embeddings: wrong number of vectors")
        return [_normalise(np.asarray(r["embedding"], dtype=np.float32)) for r in rows]

    async def embed_colbert(self, texts: list[str]) -> list[np.ndarray]:
        """Token-level vectors (tokens x dims), each row L2-normalised."""
        data = await self._post("/embeddings", {"model": settings.rerank_model, "input": texts})
        rows = sorted(data.get("data") or [], key=lambda r: r.get("index", 0))
        if len(rows) != len(texts):
            raise AIUnavailable("colbert: wrong number of outputs")
        out = []
        for r in rows:
            matrix = np.asarray(r["embedding"], dtype=np.float32)
            if matrix.ndim != 2 or matrix.shape[0] == 0:
                raise AIUnavailable("colbert: unexpected shape")
            out.append(_normalise(matrix))
        return out


def _normalise(x: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(x, axis=-1, keepdims=True)
    return x / np.where(norm == 0, 1, norm)


_client: LLMClient | None = None


def ai_enabled() -> bool:
    return bool(settings.llm_base_url and settings.llm_api_key)


def get_llm() -> LLMClient:
    """The shared client; raises AIUnavailable when AI is not configured."""
    global _client
    if not ai_enabled():
        raise AIUnavailable("AI gateway not configured")
    if _client is None:
        _client = LLMClient(
            settings.llm_base_url, settings.llm_api_key, settings.llm_timeout_seconds
        )
    return _client
