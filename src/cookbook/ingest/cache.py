"""Disk cache around any Transcriber.

Two reasons it exists:
- cost: the same page is never paid for twice;
- reproducibility: a model can answer differently on each call, so once a
  page has been transcribed, every later run sees the same text.
"""

import hashlib
from pathlib import Path

from cookbook.ingest.transcriber import Transcriber, Transcription


class CachedTranscriber:
    def __init__(self, inner: Transcriber, cache_dir: Path, namespace: str) -> None:
        """`namespace` must change whenever the model or the prompt changes."""
        self._inner = inner
        self._cache_dir = cache_dir
        self._namespace = namespace

    def transcribe(self, image: bytes, media_type: str) -> Transcription:
        entry = self._entry_path(image)
        if entry.exists():
            cached = Transcription.model_validate_json(entry.read_text(encoding="utf-8"))
            return _mark_cached(cached)

        result = self._inner.transcribe(image, media_type)
        entry.parent.mkdir(parents=True, exist_ok=True)
        entry.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        return result

    def _entry_path(self, image: bytes) -> Path:
        digest = hashlib.sha256(self._namespace.encode("utf-8") + b"\0" + image).hexdigest()
        return self._cache_dir / f"{digest}.json"


def _mark_cached(transcription: Transcription) -> Transcription:
    if transcription.usage is None:
        return transcription
    usage = transcription.usage.model_copy(update={"cached": True})
    return transcription.model_copy(update={"usage": usage})
