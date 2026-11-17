"""The web endpoint, run against a scripted model (no API calls).

Skipped unless the optional web packages are installed: uv sync --extra web
"""

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from cookbook.extract import Extractor  # noqa: E402
from cookbook.extract.schema import WireServings  # noqa: E402
from cookbook.ingest import ImageReader, Ingestor, PdfReader, TextReader  # noqa: E402
from cookbook.models import InputKind  # noqa: E402
from cookbook.web.app import create_app  # noqa: E402
from fakes import FakeTranscriber  # noqa: E402
from test_extractor import TEXT, ScriptedModel, wire  # noqa: E402


def client(answer=None):
    transcriber = FakeTranscriber()
    ingestor = Ingestor(
        {InputKind.TEXT: TextReader(), InputKind.PDF: PdfReader(transcriber), InputKind.IMAGE: ImageReader(transcriber)}
    )
    app = create_app(
        ingestor_factory=lambda: ingestor,
        extractor_factory=lambda: Extractor(ScriptedModel(answer or wire())),
    )
    return TestClient(app)


def post(test_client, content=TEXT.encode("utf-8"), **form):
    return test_client.post("/api/run", files={"file": ("marinade.txt", content, "text/plain")}, data=form)


def test_page_is_served():
    response = client().get("/")
    assert response.status_code == 200
    assert "<title>Cookbook</title>" in response.text


def test_extraction_returns_the_recipe_with_provenance():
    view = post(client()).json()
    ingredient = view["recipe"]["ingredients"][0]
    assert view["is_recipe"] and view["document"]["name"] == "marinade.txt"
    assert ingredient["amount"] == "4"
    assert ingredient["source"] == {"kind": "read", "page": 1, "text": "4 Zwiebeln"}
    assert view["recipe"]["servings"]["source"]["kind"] == "guessed"
    assert "# Marinade" in view["markdown"]


def test_vegan_and_servings_are_applied_and_explained():
    view = post(client(), vegan="true", servings="6").json()
    assert view["recipe"]["servings"]["value"] == 6
    assert view["recipe"]["ingredients"][0]["scaled"]
    assert any(c["rule"] == "scale" for c in view["recipe"]["changes"])


def test_unknown_servings_without_an_assumption_is_a_clear_error():
    missing = wire(servings=WireServings(value=0, evidence="missing", page=0, quote="", note=""))
    response = post(client(missing), servings="6")
    assert response.status_code == 400
    assert "assume-servings" in response.json()["detail"]


def test_unknown_servings_with_an_assumption_scales():
    missing = wire(servings=WireServings(value=0, evidence="missing", page=0, quote="", note=""))
    view = post(client(missing), servings="6", assume_servings="3").json()
    assert view["recipe"]["servings"]["value"] == 6


def test_not_a_recipe_is_reported():
    view = post(client(wire(is_recipe=False, ingredients=[], steps=[]))).json()
    assert view["is_recipe"] is False
    assert "recipe" not in view


def test_unsupported_file_is_rejected():
    response = post(client(), content=b"\x00\x01\x02\xff")
    assert response.status_code == 400
    assert "not a PDF" in response.json()["detail"]


def test_empty_file_is_rejected():
    assert post(client(), content=b"").status_code == 400


def test_preparation_already_in_the_name_is_not_repeated():
    from cookbook.extract.schema import WireIngredient, WireQuantity

    onion = WireIngredient(
        id="onion", name="onion", name_original="Zwiebeln, finely chopped",
        quantity=WireQuantity(kind="exact", value=4, max_value=0, unit="", raw="4"),
        preparation="finely chopped", optional=False, is_intermediate=False,
        evidence="read", page=1, quote="4 Zwiebeln", note="",
    )
    view = post(client(wire([onion]))).json()
    assert view["recipe"]["ingredients"][0]["preparation"] is None
