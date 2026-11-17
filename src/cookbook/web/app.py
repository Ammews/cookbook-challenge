"""A small local web front end: upload a recipe, pick vegan and servings, see the result.

It only calls the same pipeline as the CLI. Nothing here knows about recipes.
"""

import tempfile
from collections.abc import Callable
from pathlib import Path

import anthropic
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from cookbook.config import Settings
from cookbook.extract import ExtractionError, Extractor, build_extractor
from cookbook.ingest import Ingestor, TranscriptionError, UnsupportedInputError, build_ingestor
from cookbook.manipulate import ConvertToMetric, MakeVegan, ManipulationError, ScaleServings
from cookbook.pipeline import run_pipeline
from cookbook.web.view import build_view

_PAGE = Path(__file__).with_name("index.html")
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


def create_app(
    ingestor_factory: Callable[[], Ingestor] | None = None,
    extractor_factory: Callable[[], Extractor] | None = None,
) -> FastAPI:
    """Factories are injectable so tests can run the endpoint without a model."""
    settings = Settings.from_env()
    make_ingestor = ingestor_factory or (lambda: build_ingestor(settings))
    make_extractor = extractor_factory or (lambda: build_extractor(settings))
    app = FastAPI(title="Cookbook", docs_url=None, redoc_url=None)

    @app.get("/")
    def page() -> FileResponse:
        return FileResponse(_PAGE, media_type="text/html")

    @app.post("/api/run")
    def run(
        file: UploadFile = File(...),
        vegan: bool = Form(False),
        metric: bool = Form(False),
        servings: int | None = Form(None),
        assume_servings: int | None = Form(None),
    ) -> dict:
        data = file.file.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "File is larger than 20 MB.")
        if not data:
            raise HTTPException(400, "The file is empty.")

        rules = []
        if vegan:
            rules.append(MakeVegan())
        if servings:
            rules.append(ScaleServings(servings, assume_base=assume_servings))
        if metric:
            rules.append(ConvertToMetric())  # last, so rounding happens once

        # Keep the original name: the pipeline reports it, and the extension does not decide the type.
        name = Path(file.filename or "upload").name
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / name
            path.write_bytes(data)
            try:
                result = run_pipeline(path, make_ingestor(), make_extractor(), rules)
            except (UnsupportedInputError, ManipulationError) as error:
                raise HTTPException(400, str(error)) from error
            except (TranscriptionError, ExtractionError) as error:
                raise HTTPException(502, str(error)) from error
            except anthropic.APIError as error:
                raise HTTPException(502, f"Anthropic API error: {error}") from error
        return build_view(result)

    return app
