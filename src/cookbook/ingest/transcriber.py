"""The contract for turning a page image into text.

Readers depend on this protocol, not on a concrete model, so the provider can
be swapped and tests can run with a fake that never calls an API.
"""

from typing import Protocol

from cookbook.models import LlmUsage
from cookbook.models.base import DomainModel


class Transcription(DomainModel):
    text: str
    decoration_text: tuple[str, ...] = ()
    uncertain: tuple[str, ...] = ()
    usage: LlmUsage | None = None


class TranscriptionError(RuntimeError):
    """The model did not return a usable transcription."""


class Transcriber(Protocol):
    def transcribe(self, image: bytes, media_type: str) -> Transcription:
        """Return the text visible in one page image."""
        ...
