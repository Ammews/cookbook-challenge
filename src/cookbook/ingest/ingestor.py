"""Stage 1: detect what came in and route it to the right reader."""

from collections.abc import Mapping
from pathlib import Path

from cookbook.ingest.detect import detect_kind
from cookbook.ingest.readers import Reader
from cookbook.models import Document, InputKind


class Ingestor:
    """Routes a file to the reader registered for its kind.

    Supporting a new format means registering a new reader; this class and
    the existing readers stay untouched.
    """

    def __init__(self, readers: Mapping[InputKind, Reader]) -> None:
        self._readers = dict(readers)

    def ingest(self, path: Path) -> Document:
        kind = detect_kind(path)
        pages = self._readers[kind].read(path)
        return Document(name=path.name, kind=kind, pages=pages)
