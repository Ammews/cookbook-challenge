import pytest

from cookbook.ingest import UnsupportedInputError, detect_kind
from cookbook.models import InputKind
from samples import make_image, make_pdf


def test_pdf_is_detected(tmp_path):
    assert detect_kind(make_pdf(tmp_path / "a.pdf", ["hello"])) is InputKind.PDF


def test_png_and_jpeg_are_detected(tmp_path):
    assert detect_kind(make_image(tmp_path / "a.png")) is InputKind.IMAGE
    assert detect_kind(make_image(tmp_path / "a.jpg")) is InputKind.IMAGE


def test_text_is_detected(tmp_path):
    path = tmp_path / "recipe.txt"
    path.write_text("200 g Mehl, 2 Eier", encoding="utf-8")
    assert detect_kind(path) is InputKind.TEXT


def test_content_wins_over_a_misleading_extension(tmp_path):
    path = make_pdf(tmp_path / "recipe.txt", ["hello"])
    assert detect_kind(path) is InputKind.PDF


def test_unknown_binary_is_rejected(tmp_path):
    path = tmp_path / "data.bin"
    path.write_bytes(b"\x00\x01\x02\xff\xfe")
    with pytest.raises(UnsupportedInputError, match="not a PDF, an image or UTF-8 text"):
        detect_kind(path)


def test_empty_file_is_rejected(tmp_path):
    path = tmp_path / "empty.txt"
    path.write_bytes(b"  \n")
    with pytest.raises(UnsupportedInputError, match="is empty"):
        detect_kind(path)
