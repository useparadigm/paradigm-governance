"""LLM provider abstraction for Anthropic and OpenAI APIs."""
from __future__ import annotations

import json
import os
import sys
from abc import ABC, abstractmethod

import httpx

from code_governance.advisor.schemas import AdviceReport

DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
DEFAULT_OPENAI_MODEL = "gpt-4o"
REQUEST_TIMEOUT = 60


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, system: str, user: str) -> AdviceReport:
        """Send a prompt to the LLM and return structured advice."""
        ...


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str, model: str | None = None):
        self.api_key = api_key
        self.model = model or os.environ.get("GOVERNANCE_LLM_MODEL", DEFAULT_ANTHROPIC_MODEL)

    def complete(self, system: str, user: str) -> AdviceReport:
        schema = AdviceReport.model_json_schema()

        response = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": 4096,
                "system": system,
                "messages": [{"role": "user", "content": user}],
                "tools": [
                    {
                        "name": "provide_advice",
                        "description": "Provide architectural advice for governance violations and new modules.",
                        "input_schema": schema,
                    }
                ],
                "tool_choice": {"type": "tool", "name": "provide_advice"},
            },
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()
        data = response.json()

        _log_usage(data.get("usage", {}))

        for block in data.get("content", []):
            if block.get("type") == "tool_use":
                return AdviceReport.model_validate(block["input"])

        raise RuntimeError("No tool_use block in Anthropic response")


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, model: str | None = None):
        self.api_key = api_key
        self.model = model or os.environ.get("GOVERNANCE_LLM_MODEL", DEFAULT_OPENAI_MODEL)

    def complete(self, system: str, user: str) -> AdviceReport:
        schema = _make_openai_strict_schema(AdviceReport.model_json_schema())

        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "advice_report",
                        "strict": True,
                        "schema": schema,
                    },
                },
            },
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()
        data = response.json()

        _log_usage(data.get("usage", {}))

        content = data["choices"][0]["message"]["content"]
        return AdviceReport.model_validate_json(content)


def get_provider() -> LLMProvider:
    """Select and return the appropriate LLM provider based on env vars."""
    provider_override = os.environ.get("GOVERNANCE_LLM_PROVIDER", "").lower()
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    openai_key = os.environ.get("OPENAI_API_KEY", "")

    if provider_override == "anthropic":
        if not anthropic_key:
            raise ConfigError("GOVERNANCE_LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set")
        return AnthropicProvider(anthropic_key)
    elif provider_override == "openai":
        if not openai_key:
            raise ConfigError("GOVERNANCE_LLM_PROVIDER=openai but OPENAI_API_KEY is not set")
        return OpenAIProvider(openai_key)
    elif anthropic_key:
        return AnthropicProvider(anthropic_key)
    elif openai_key:
        return OpenAIProvider(openai_key)
    else:
        raise ConfigError(
            "No LLM API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY to use --advise.\n"
            "  export ANTHROPIC_API_KEY=sk-ant-...\n"
            "  export OPENAI_API_KEY=sk-..."
        )


class ConfigError(Exception):
    """Raised when LLM provider configuration is missing or invalid."""
    pass


def _make_openai_strict_schema(schema: dict) -> dict:
    """Patch a JSON schema for OpenAI strict mode.

    OpenAI requires additionalProperties=false on all objects,
    all properties must be required, and no defaults.
    """
    schema = schema.copy()

    def _patch(obj: dict) -> dict:
        obj = obj.copy()
        if obj.get("type") == "object":
            obj["additionalProperties"] = False
            if "properties" in obj:
                obj["required"] = list(obj["properties"].keys())
                obj["properties"] = {
                    k: _patch(v) for k, v in obj["properties"].items()
                }
        if "items" in obj:
            obj["items"] = _patch(obj["items"])
        if "$defs" in obj:
            obj["$defs"] = {k: _patch(v) for k, v in obj["$defs"].items()}
        # Remove defaults — strict mode doesn't allow them
        obj.pop("default", None)
        obj.pop("title", None)
        return obj

    return _patch(schema)


def _log_usage(usage: dict) -> None:
    """Log token usage to stderr."""
    input_tokens = usage.get("input_tokens") or usage.get("prompt_tokens", 0)
    output_tokens = usage.get("output_tokens") or usage.get("completion_tokens", 0)
    if input_tokens or output_tokens:
        print(
            f"Advice generated ({input_tokens:,} input / {output_tokens:,} output tokens)",
            file=sys.stderr,
        )
