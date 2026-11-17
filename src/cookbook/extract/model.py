"""The model call behind extraction, and a disk cache around it.

The extractor depends on the `ExtractionModel` protocol, so tests use a fake
and the provider can be swapped without touching the extraction logic.
"""

import hashlib
import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

import anthropic
from pydantic import BaseModel

from cookbook.extract.prompt import PROMPT_VERSION, SYSTEM_PROMPT
from cookbook.extract.schema import WireExtraction
from cookbook.models import LlmUsage

_MAX_TOKENS = 16000


class ExtractionError(RuntimeError):
    """The model did not return a usable extraction."""


class ModelReply(BaseModel):
    extraction: WireExtraction
    usage: LlmUsage


class ExtractionModel(Protocol):
    def extract(self, messages: list[dict]) -> ModelReply: ...


class ClaudeExtractionModel:
    def __init__(
        self, model: str, client_factory: Callable[[], anthropic.Anthropic] = anthropic.Anthropic
    ) -> None:
        self._model = model
        self._client_factory = client_factory
        self._client: anthropic.Anthropic | None = None

    @property
    def cache_namespace(self) -> str:
        return f"{self._model}/extract-prompt-v{PROMPT_VERSION}"

    def extract(self, messages: list[dict]) -> ModelReply:
        started = time.perf_counter()
        try:
            response = self._get_client().messages.parse(
                model=self._model,
                max_tokens=_MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=messages,
                output_format=WireExtraction,
            )
        except TypeError as error:
            if "authentication" not in str(error):
                raise
            raise ExtractionError(
                "no Anthropic credentials found; copy .env.example to .env and set ANTHROPIC_API_KEY"
            ) from error
        if response.stop_reason != "end_turn":
            raise ExtractionError(f"model stopped with '{response.stop_reason}' before finishing")
        if response.parsed_output is None:
            raise ExtractionError("model returned no structured extraction")
        return ModelReply(
            extraction=response.parsed_output,
            usage=LlmUsage(
                model=self._model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                seconds=time.perf_counter() - started,
            ),
        )

    def _get_client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = self._client_factory()
        return self._client


class CachedExtractionModel:
    """Same request, same answer: a later run never pays twice and never drifts."""

    def __init__(self, inner: ExtractionModel, cache_dir: Path, namespace: str) -> None:
        self._inner = inner
        self._cache_dir = cache_dir
        self._namespace = namespace

    def extract(self, messages: list[dict]) -> ModelReply:
        key = hashlib.sha256(
            (self._namespace + "\0" + json.dumps(messages, sort_keys=True, ensure_ascii=False)).encode("utf-8")
        ).hexdigest()
        entry = self._cache_dir / f"{key}.json"
        if entry.exists():
            reply = ModelReply.model_validate_json(entry.read_text(encoding="utf-8"))
            return reply.model_copy(update={"usage": reply.usage.model_copy(update={"cached": True})})
        reply = self._inner.extract(messages)
        entry.parent.mkdir(parents=True, exist_ok=True)
        entry.write_text(reply.model_dump_json(indent=2), encoding="utf-8")
        return reply
