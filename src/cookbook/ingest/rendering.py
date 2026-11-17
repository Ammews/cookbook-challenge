"""Turn PDF pages and image files into JPEGs a vision model can read.

Both paths cap the longest side. The cap matters for cost: image tokens grow
with resolution, and past a point extra pixels stop improving what the model
can read.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pymupdf

JPEG_MEDIA_TYPE = "image/jpeg"
_JPEG_QUALITY = 90
# A PDF page is measured in points (72 per inch). Rendering a scan below
# its native resolution loses detail, far above it only adds cost.
_MAX_PDF_ZOOM = 4.0


@contextmanager
def open_pdf_pages(path: Path) -> Iterator[list[pymupdf.Page]]:
    document = pymupdf.open(path)
    try:
        yield list(document)
    finally:
        document.close()


def pdf_page_to_jpeg(page: pymupdf.Page, max_edge: int) -> bytes:
    """Render a PDF page so its longest side is at most `max_edge` pixels."""
    zoom = min(max_edge / max(page.rect.width, page.rect.height), _MAX_PDF_ZOOM)
    pixmap = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
    return pixmap.tobytes("jpeg", jpg_quality=_JPEG_QUALITY)


def image_file_to_jpeg(path: Path, max_edge: int) -> bytes:
    """Re-encode an image file, shrinking it only if it exceeds `max_edge`.

    An image is never enlarged: it has only the pixels it has, so upscaling
    would add cost without adding anything to read.
    """
    pixmap = pymupdf.Pixmap(str(path))
    if pixmap.alpha:
        pixmap = pymupdf.Pixmap(pixmap, 0)  # JPEG has no alpha channel
    if pixmap.colorspace is not None and pixmap.colorspace.n > 3:
        pixmap = pymupdf.Pixmap(pymupdf.csRGB, pixmap)  # e.g. CMYK scans
    longest = max(pixmap.width, pixmap.height)
    if longest > max_edge:
        scale = max_edge / longest
        pixmap = pymupdf.Pixmap(
            pixmap, round(pixmap.width * scale), round(pixmap.height * scale), None
        )
    return pixmap.tobytes("jpeg", jpg_quality=_JPEG_QUALITY)
