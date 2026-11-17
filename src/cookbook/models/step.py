"""One instruction of the method, linked to the ingredients and tools it uses."""

from pydantic import Field, model_validator

from cookbook.models.base import DomainModel, NonEmptyStr, Slug
from cookbook.models.source import Source


class Duration(DomainModel):
    """A time span as written, with minutes only when the text gives a number."""

    raw: NonEmptyStr = Field(description='As written, e.g. "eine Stunde", "langsam".')
    min_minutes: float | None = Field(default=None, gt=0)
    max_minutes: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _range_is_ordered(self) -> "Duration":
        if (self.min_minutes is None) != (self.max_minutes is None):
            raise ValueError("give both min_minutes and max_minutes, or neither")
        if self.min_minutes is not None and self.min_minutes > self.max_minutes:
            raise ValueError("min_minutes cannot be greater than max_minutes")
        return self


class Step(DomainModel):
    order: int = Field(ge=1, description="1-based position in the method.")
    text: NonEmptyStr
    ingredient_ids: tuple[Slug, ...] = ()
    tool_ids: tuple[Slug, ...] = ()
    duration: Duration | None = None
    condition: str | None = Field(
        default=None,
        description='When this step applies, e.g. "if the roast is used after 8 days".',
    )
    source: Source
