"""Pots, pans and utensils, whether the recipe names them or only implies them."""

from pydantic import Field

from cookbook.models.base import DomainModel, NonEmptyStr, Slug
from cookbook.models.source import Source, SourceStatus


class Tool(DomainModel):
    id: Slug
    name: NonEmptyStr
    source: Source = Field(
        description="status 'read' for a tool the text names, 'inferred' for an implied one."
    )

    @property
    def stated(self) -> bool:
        """True if the recipe names this tool; False if it is only implied."""
        return self.source.status is SourceStatus.READ
