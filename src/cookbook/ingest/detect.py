"""Decide what kind of file came in by looking at its bytes, not its name."""

from pathlib import Path

from cookbook.models import InputKind

_IMAGE_SIGNATURES = (
    b"\x89PNG\r\n\x1a\n",
    b"\xff\xd8\xff",  # JPEG
    b"GIF87a",
    b"GIF89a",
)


class UnsupportedInputError(ValueError):
    """The file is not a PDF, an image or readable text."""


def detect_kind(path: Path) -> InputKind:
    """Classify a file from its content.

    File extensions lie (a scan saved as `.txt`, a PDF with no extension), so
    the decision uses magic bytes, and falls back to "is this valid UTF-8 text".
    """
    data = path.read_bytes()
    if not data.strip():
        raise UnsupportedInputError(f"{path.name} is empty")
    if data.startswith(b"%PDF-"):
        return InputKind.PDF
    if data.startswith(_IMAGE_SIGNATURES) or _is_webp(data):
        return InputKind.IMAGE
    if _is_text(data):
        return InputKind.TEXT
    raise UnsupportedInputError(f"{path.name} is not a PDF, an image or UTF-8 text")


def _is_webp(data: bytes) -> bool:
    return data[:4] == b"RIFF" and data[8:12] == b"WEBP"


def _is_text(data: bytes) -> bool:
    if b"\x00" in data:
        return False
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True
