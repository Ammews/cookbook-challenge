"""Provenance: where a value came from and whether it was read or guessed."""

from enum import StrEnum

from pydantic import Field, model_validator

from cookbook.models.base import DomainModel


class SourceStatus(StrEnum):
    READ = "read"          # literally written in the document
    INFERRED = "inferred"  # not written; deduced, and must say why
    MISSING = "missing"    # the document does not give this value
    RULE = "rule"          # set by a manipulation rule (scaling, vegan); must say which and why


class Source(DomainModel):
    """Traceability for one extracted value.

    The rules below are structural only. Whether `quote` really appears in
    the document is checked later by the grounding validator, which has
    access to the transcribed text.
    """

    status: SourceStatus
    page: int | None = Field(
        default=None, ge=1, description="1-based page number, if the input has pages."
    )
    quote: str | None = Field(
        default=None,
        description="Verbatim text from the document that supports this value.",
    )
    note: str | None = Field(
        default=None,
        description="Reasoning for an inferred value, or what is missing.",
    )

    @model_validator(mode="after")
    def _status_matches_evidence(self) -> "Source":
        has_quote = bool(self.quote and self.quote.strip())
        has_note = bool(self.note and self.note.strip())
        if self.status is SourceStatus.READ and not has_quote:
            raise ValueError("a value marked 'read' must carry the quote it was read from")
        if self.status in (SourceStatus.INFERRED, SourceStatus.RULE) and not has_note:
            raise ValueError(
                f"a value marked '{self.status.value}' must explain the reasoning in 'note'"
            )
        if self.status is SourceStatus.MISSING and has_quote:
            raise ValueError("a value marked 'missing' cannot have a quote")
        return self

    @property
    def is_guess(self) -> bool:
        """True when the value was not read directly from the document."""
        return self.status is not SourceStatus.READ
