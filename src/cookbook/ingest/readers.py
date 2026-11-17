"""One reader per input kind. Each turns a file into pages of text."""

from pathlib import Path
from typing import Protocol

from cookbook.ingest.rendering import (
    JPEG_MEDIA_TYPE,
    image_file_to_jpeg,
    open_pdf_pages,
    pdf_page_to_jpeg,
)
from cookbook.ingest.transcriber import Transcriber, Transcription
from cookbook.models import Page, ReadMethod

DEFAULT_MAX_IMAGE_EDGE = 2000
# A scanned page can still carry a few stray characters (a stamp, a page
# number added by the scanner). Below this, the text layer is not the content.
MIN_TEXT_LAYER_CHARS = 40


class Reader(Protocol):
    def read(self, path: Path) -> tuple[Page, ...]: ...


class TextReader:
    def read(self, path: Path) -> tuple[Page, ...]:
        text = path.read_text(encoding="utf-8-sig")
        return (Page(number=1, text=text.strip(), method=ReadMethod.PLAIN_TEXT),)


class PdfReader:
    """Reads each page from its text layer when it has one, by vision when not.

    The decision is per page, not per file: a PDF can mix exported pages with
    scanned ones, and a text layer is exact and free where it exists.
    """

    def __init__(
        self,
        transcriber: Transcriber,
        max_image_edge: int = DEFAULT_MAX_IMAGE_EDGE,
        min_text_layer_chars: int = MIN_TEXT_LAYER_CHARS,
    ) -> None:
        self._transcriber = transcriber
        self._max_image_edge = max_image_edge
        self._min_text_layer_chars = min_text_layer_chars

    def read(self, path: Path) -> tuple[Page, ...]:
        with open_pdf_pages(path) as pdf_pages:
            return tuple(
                self._read_page(number, pdf_page)
                for number, pdf_page in enumerate(pdf_pages, start=1)
            )

    def _read_page(self, number: int, pdf_page) -> Page:
        text = pdf_page.get_text().strip()
        if len(text) >= self._min_text_layer_chars:
            return Page(number=number, text=text, method=ReadMethod.PDF_TEXT_LAYER)
        image = pdf_page_to_jpeg(pdf_page, self._max_image_edge)
        return _vision_page(number, self._transcriber.transcribe(image, JPEG_MEDIA_TYPE))


class ImageReader:
    def __init__(
        self, transcriber: Transcriber, max_image_edge: int = DEFAULT_MAX_IMAGE_EDGE
    ) -> None:
        self._transcriber = transcriber
        self._max_image_edge = max_image_edge

    def read(self, path: Path) -> tuple[Page, ...]:
        image = image_file_to_jpeg(path, self._max_image_edge)
        return (_vision_page(1, self._transcriber.transcribe(image, JPEG_MEDIA_TYPE)),)


def _vision_page(number: int, transcription: Transcription) -> Page:
    return Page(
        number=number,
        text=transcription.text.strip(),
        method=ReadMethod.VISION,
        decoration_text=transcription.decoration_text,
        uncertain=transcription.uncertain,
        usage=transcription.usage,
    )
