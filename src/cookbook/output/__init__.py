"""Stage 4: output. Markdown for the cook, JSON for machines."""

from pathlib import Path

from cookbook.output.markdown import render_markdown
from cookbook.pipeline import PipelineResult

__all__ = ["render_markdown", "write_outputs"]


def write_outputs(result: PipelineResult, folder: Path, stem: str) -> tuple[Path, Path]:
    folder.mkdir(parents=True, exist_ok=True)
    markdown = folder / f"{stem}.md"
    data = folder / f"{stem}.json"
    markdown.write_text(render_markdown(result), encoding="utf-8")
    data.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return markdown, data
