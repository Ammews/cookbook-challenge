"""One change made by a manipulation rule, so the cook can see what changed and why."""

from pydantic import Field

from cookbook.models.base import DomainModel, NonEmptyStr


class Change(DomainModel):
    rule: NonEmptyStr = Field(description='Rule that made the change, e.g. "scale", "vegan".')
    target: NonEmptyStr = Field(description="What changed: an ingredient, a step, the servings.")
    before: str
    after: str
    reason: NonEmptyStr
