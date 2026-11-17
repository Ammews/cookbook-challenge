"""Transcriber backed by a Claude vision model."""

import base64
import time
from collections.abc import Callable

import anthropic
from pydantic import BaseModel, Field

from cookbook.ingest.transcriber import Transcription, TranscriptionError
from cookbook.models import LlmUsage

# Bump when the prompt changes, so cached transcriptions made with the old
# prompt are not reused.
PROMPT_VERSION = "1"

_MAX_TOKENS = 8000

_SYSTEM_PROMPT = """\
You transcribe one page of a document so that a later step can extract a recipe from it.
The page may be handwritten, old, photographed at an angle, or decorated with drawings.

Rules:
- Transcribe only what is written on the page. Never add, complete or summarise.
- Keep the original language and spelling, including old or regional spellings. Do not translate or correct.
- Follow reading order. Write running text as paragraphs, not line by line.
- When a word is split by a hyphen at the end of a line, join it back into one word.
- Put the running text of the page in `text`.
- Put everything that is written on the page but is not running text in `decoration_text`: \
labels inside drawings, captions, page numbers, decorative headers. One entry per item.
- If you are not sure about a word, write your best reading followed by [?] in `text`, \
and list that word in `uncertain`.
- If a word is unreadable, write [illegible] in its place.
- If the page has no text, return an empty `text`.
"""

_USER_PROMPT = "Transcribe this page."


class _TranscriptionOutput(BaseModel):
    """Shape the model must answer in. Kept separate from the domain model so
    the wire format can change without touching the rest of the pipeline."""

    text: str = Field(description="Running text of the page, in reading order.")
    decoration_text: list[str] = Field(
        description="Text inside drawings, captions, page numbers, decorative headers."
    )
    uncertain: list[str] = Field(description="Words whose reading is not certain.")


class ClaudeTranscriber:
    def __init__(
        self,
        model: str,
        client_factory: Callable[[], anthropic.Anthropic] = anthropic.Anthropic,
    ) -> None:
        self._model = model
        # The client is created on first use, so inputs that need no model
        # (text files, digital PDFs) work without an API key.
        self._client_factory = client_factory
        self._client: anthropic.Anthropic | None = None

    @property
    def cache_namespace(self) -> str:
        """Identifies everything that shapes the output besides the image."""
        return f"{self._model}/prompt-v{PROMPT_VERSION}"

    def transcribe(self, image: bytes, media_type: str) -> Transcription:
        started = time.perf_counter()
        try:
            response = self._request(image, media_type)
        except TypeError as error:
            # The SDK raises a bare TypeError when it finds no credentials.
            if "authentication" not in str(error):
                raise
            raise TranscriptionError(
                "no Anthropic credentials found; copy .env.example to .env "
                "and set ANTHROPIC_API_KEY"
            ) from error
        seconds = time.perf_counter() - started

        if response.stop_reason != "end_turn":
            raise TranscriptionError(
                f"model stopped with '{response.stop_reason}' instead of finishing the transcription"
            )
        output = response.parsed_output
        if output is None:
            raise TranscriptionError("model returned no structured transcription")

        return Transcription(
            text=output.text,
            decoration_text=tuple(output.decoration_text),
            uncertain=tuple(output.uncertain),
            usage=LlmUsage(
                model=self._model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                seconds=seconds,
            ),
        )

    def _request(self, image: bytes, media_type: str):
        return self._get_client().messages.parse(
            model=self._model,
            max_tokens=_MAX_TOKENS,
            system=_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64.standard_b64encode(image).decode("ascii"),
                            },
                        },
                        {"type": "text", "text": _USER_PROMPT},
                    ],
                }
            ],
            output_format=_TranscriptionOutput,
        )

    def _get_client(self) -> anthropic.Anthropic:
        if self._client is None:
            self._client = self._client_factory()
        return self._client
