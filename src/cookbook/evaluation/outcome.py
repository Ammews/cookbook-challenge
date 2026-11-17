"""What the pipeline produced for one document, as seen by the checks."""

from pydantic import Field

from cookbook.models import Recipe
from cookbook.models.base import DomainModel


class Outcome(DomainModel):
    is_recipe: bool
    recipes_in_document: int = Field(default=1, ge=0)
    recipe: Recipe | None = None
