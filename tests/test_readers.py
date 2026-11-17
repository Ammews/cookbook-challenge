from cookbook.ingest import ImageReader, Ingestor, PdfReader, TextReader
from cookbook.models import InputKind, ReadMethod
from fakes import FakeTranscriber
from samples import LONG_TEXT, image_size, make_image, make_pdf


def test_text_file_is_read_without_a_model(tmp_path):
    path = tmp_path / "recipe.txt"
    path.write_text("﻿200 g Mehl\n", encoding="utf-8")

    (page,) = TextReader().read(path)

    assert page.text == "200 g Mehl"
    assert page.method is ReadMethod.PLAIN_TEXT
    assert page.usage is None


def test_digital_pdf_uses_its_text_layer_and_never_calls_the_model(tmp_path):
    transcriber = FakeTranscriber()

    (page,) = PdfReader(transcriber).read(make_pdf(tmp_path / "a.pdf", [LONG_TEXT]))

    assert page.method is ReadMethod.PDF_TEXT_LAYER
    assert "Zwiebeln" in page.text
    assert transcriber.calls == []


def test_pdf_page_without_text_layer_is_transcribed(tmp_path):
    transcriber = FakeTranscriber("Sauerbraten")

    (page,) = PdfReader(transcriber).read(make_pdf(tmp_path / "scan.pdf", [None]))

    assert page.method is ReadMethod.VISION
    assert page.text == "Sauerbraten"
    assert page.decoration_text == ("Rosinen",)
    assert page.uncertain == ("garbrötscheln",)
    assert page.usage.model == "fake-model"
    assert transcriber.calls[0][1] == "image/jpeg"


def test_pdf_routing_is_decided_per_page(tmp_path):
    transcriber = FakeTranscriber()

    pages = PdfReader(transcriber).read(make_pdf(tmp_path / "mixed.pdf", [LONG_TEXT, None]))

    assert [p.method for p in pages] == [ReadMethod.PDF_TEXT_LAYER, ReadMethod.VISION]
    assert [p.number for p in pages] == [1, 2]
    assert len(transcriber.calls) == 1


def test_a_few_stray_characters_do_not_count_as_a_text_layer(tmp_path):
    transcriber = FakeTranscriber()

    (page,) = PdfReader(transcriber).read(make_pdf(tmp_path / "scan.pdf", ["188"]))

    assert page.method is ReadMethod.VISION


def test_rendered_page_respects_the_size_cap(tmp_path):
    transcriber = FakeTranscriber()

    PdfReader(transcriber, max_image_edge=800).read(make_pdf(tmp_path / "scan.pdf", [None]))

    assert max(image_size(transcriber.calls[0][0])) <= 800


def test_large_image_is_downscaled(tmp_path):
    transcriber = FakeTranscriber()

    ImageReader(transcriber, max_image_edge=500).read(make_image(tmp_path / "a.png", 2000, 1000))

    assert image_size(transcriber.calls[0][0]) == (500, 250)


def test_small_image_is_not_upscaled(tmp_path):
    transcriber = FakeTranscriber()

    (page,) = ImageReader(transcriber, max_image_edge=2000).read(
        make_image(tmp_path / "a.png", 300, 200)
    )

    assert image_size(transcriber.calls[0][0]) == (300, 200)
    assert page.method is ReadMethod.VISION


def test_ingestor_routes_by_detected_kind(tmp_path):
    transcriber = FakeTranscriber()
    ingestor = Ingestor(
        {
            InputKind.TEXT: TextReader(),
            InputKind.PDF: PdfReader(transcriber),
            InputKind.IMAGE: ImageReader(transcriber),
        }
    )
    text_path = tmp_path / "r.txt"
    text_path.write_text("2 Eier", encoding="utf-8")

    assert ingestor.ingest(text_path).kind is InputKind.TEXT
    assert ingestor.ingest(make_image(tmp_path / "r.png")).kind is InputKind.IMAGE
    document = ingestor.ingest(make_pdf(tmp_path / "r.pdf", [LONG_TEXT, None]))
    assert (document.name, document.kind, len(document.pages)) == ("r.pdf", InputKind.PDF, 2)
