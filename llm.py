"""MiniMax API client for LLM completions."""
import httpx
from typing import Any

from config import get_settings


class MinimaxClient:
    """Client for MiniMax Text API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.minimax.io/anthropic",
    ):
        settings = get_settings()
        self.api_key = api_key or settings.minimax_api_key
        self.base_url = base_url
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy initialization of HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"x-api-key": self.api_key},
                timeout=60.0,
            )
        return self._client

    async def complete(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Send a completion request to MiniMax."""
        client = await self._get_client()

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": "MiniMax-M2.7",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        response = await client.post("/v1/messages", json=payload)
        response.raise_for_status()
        data = response.json()

        # MiniMax follows Anthropic format with thinking + text blocks
        if "content" in data:
            for block in data["content"]:
                if block.get("type") == "text":
                    return block.get("text", "")
        return ""

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
