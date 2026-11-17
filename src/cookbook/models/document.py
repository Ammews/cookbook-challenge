"""The ingested document: page texts plus how each page was read."""

from enum import StrEnum

from pydantic import Field, model_validator

from cookbook.models.base import DomainModel, NonEmptyStr


class InputKind(StrEnum):
    TEXT = "text"
    PDF = "pdf"
    IMAGE = "image"


class ReadMethod(StrEnum):
    PLAIN_TEXT = "plain_text"          # read straight from a text file
    PDF_TEXT_LAYER = "pdf_text_layer"  # embedded text of a digital PDF
    VISION = "vision"                  # transcribed from pixels by a vision model


class LlmUsage(DomainModel):
    """What one model call cost, so a run can report cost and latency."""

    model: NonEmptyStr
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    seconds: float = Field(ge=0)
    cached: bool = Field(
        default=False, description="True when served from the local cache (no API call)."
    )


class Page(DomainModel):
    number: int = Field(ge=1)
    text: str
    method: ReadMethod
    decoration_text: tuple[str, ...] = Field(
        default=(),
        description=(
            "Text that is on the page but not part of the running text: labels "
            "inside drawings, page numbers, headers. Kept apart so it cannot "
            "be mistaken for recipe content."
        ),
    )
    uncertain: tuple[str, ...] = Field(
        default=(), description="Words the reader was not sure about."
    )
    usage: LlmUsage | None = None

    @property
    def is_transcribed(self) -> bool:
        """True if a model produced this text, so it may contain misreadings."""
        return self.method is ReadMethod.VISION


class Document(DomainModel):
    name: NonEmptyStr
    kind: InputKind
    pages: tuple[Page, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _pages_are_sequential(self) -> "Document":
        numbers = [p.number for p in self.pages]
        if numbers != list(range(1, len(numbers) + 1)):
            raise ValueError(f"page numbers must be 1..{len(numbers)} in sequence, got {numbers}")
        return self

    @property
    def full_text(self) -> str:
        """All pages as one text, so a sentence can continue across a page break."""
        return "\n\n".join(p.text for p in self.pages if p.text.strip())
