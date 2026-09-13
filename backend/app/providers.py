import json
from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx

from app.config import Settings


class ProviderError(Exception):
    """A provider failed in a way that can be shown safely to the user."""


class ProviderUnavailable(ProviderError):
    pass


@dataclass(frozen=True)
class ProviderResponse:
    provider: str
    model: str
    tokens: AsyncIterator[str]


class OllamaProvider:
    name = "ollama"

    def __init__(self, settings: Settings):
        self.settings = settings

    async def stream(self, messages: list[dict[str, str]]) -> ProviderResponse:
        async def tokens() -> AsyncIterator[str]:
            try:
                async with httpx.AsyncClient(timeout=self.settings.model_timeout_seconds) as client:
                    async with client.stream("POST", f"{self.settings.ollama_base_url.rstrip('/')}/api/chat", json={"model": self.settings.ollama_model, "messages": messages, "stream": True}) as response:
                        response.raise_for_status()
                        async for line in response.aiter_lines():
                            if line:
                                payload = json.loads(line)
                                token = payload.get("message", {}).get("content")
                                if token:
                                    yield token
            except (httpx.HTTPError, json.JSONDecodeError) as exc:
                raise ProviderUnavailable("Local model is unavailable. Start Ollama and try again.") from exc

        return ProviderResponse(self.name, self.settings.ollama_model, tokens())


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, settings: Settings):
        self.settings = settings

    async def stream(self, messages: list[dict[str, str]]) -> ProviderResponse:
        if not self.settings.anthropic_api_key:
            raise ProviderUnavailable("Anthropic is selected but ANTHROPIC_API_KEY is not configured.")

        async def tokens() -> AsyncIterator[str]:
            try:
                from anthropic import AsyncAnthropic
                client = AsyncAnthropic(api_key=self.settings.anthropic_api_key, timeout=self.settings.model_timeout_seconds)
                system = next((item["content"] for item in messages if item["role"] == "system"), "")
                user_messages = [item for item in messages if item["role"] != "system"]
                async with client.messages.stream(model=self.settings.anthropic_model, max_tokens=1500, system=system, messages=user_messages) as stream:
                    async for text in stream.text_stream:
                        yield text
            except Exception as exc:
                raise ProviderUnavailable("Cloud model request failed. Check the API key and try again.") from exc

        return ProviderResponse(self.name, self.settings.anthropic_model, tokens())


def provider_for(name: str, settings: Settings):
    if name == "ollama":
        return OllamaProvider(settings)
    if name == "anthropic":
        return AnthropicProvider(settings)
    raise ProviderUnavailable(f"Unsupported model provider: {name}")
