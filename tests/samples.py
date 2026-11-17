"""Builds tiny input files on the fly, so no real document lives in the repo."""

from pathlib import Path

import pymupdf

LONG_TEXT = "Zum Einlegen kocht man 1/2 l Essig, 1/2 l Wasser, 4 Zwiebeln."


def make_pdf(path: Path, page_texts: list[str | None]) -> Path:
    """One page per entry. None makes a page with no text layer, like a scan."""
    document = pymupdf.open()
    for text in page_texts:
        page = document.new_page()
        if text:
            page.insert_text((72, 72), text)
    document.save(path)
    document.close()
    return path


def make_image(path: Path, width: int = 300, height: int = 200) -> Path:
    pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, width, height), False)
    pixmap.clear_with(255)
    pixmap.save(path)
    return path


def image_size(jpeg: bytes) -> tuple[int, int]:
    pixmap = pymupdf.Pixmap(jpeg)
    return pixmap.width, pixmap.height
