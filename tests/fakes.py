"""Test doubles, so no test ever calls a real model."""

from cookbook.ingest import Transcription
from cookbook.models import LlmUsage


class FakeTranscriber:
    """Returns a fixed transcription and records what it was asked."""

    def __init__(self, text: str = "transcribed text") -> None:
        self.text = text
        self.calls: list[tuple[bytes, str]] = []

    def transcribe(self, image: bytes, media_type: str) -> Transcription:
        self.calls.append((image, media_type))
        return Transcription(
            text=self.text,
            decoration_text=("Rosinen",),
            uncertain=("garbrötscheln",),
            usage=LlmUsage(model="fake-model", input_tokens=100, output_tokens=20, seconds=0.5),
        )
