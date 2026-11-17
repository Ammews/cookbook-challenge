"""Shared base for every domain model."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints


class DomainModel(BaseModel):
    """Immutable, strict base model.

    - frozen: manipulations (scale, vegan) must return new objects, never
      edit the extracted recipe in place. That keeps the original available
      for diffing and makes rules reproducible.
    - extra="forbid": a field the schema does not know is an error, not
      something silently dropped. An LLM inventing fields should fail loudly.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")


# Stable identifier used to link steps to ingredients and tools, e.g. "onion".
Slug = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_]*$", max_length=64)]

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
