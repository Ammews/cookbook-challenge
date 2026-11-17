"""The shape the model must answer in.

Kept apart from the domain models on purpose: this is a wire format, with
flat, simple fields a model fills reliably. The mapper turns it into domain
objects, where the real validation rules live.

No field is nullable. "Not given" is "" for text and 0 for numbers. The API
compiles the schema into a grammar for constrained decoding, and every
nullable field doubles its branches; the first version, with nullable
fields, was rejected as "compiled grammar is too large".
"""

from typing import Literal

from pydantic import BaseModel, Field

Kind = Literal["exact", "vague", "to_taste", "absent"]
Evidence = Literal["read", "inferred", "missing"]
Animal = Literal[
    "none", "meat", "poultry", "fish", "dairy", "egg", "honey", "gelatin", "other_animal", "uncertain"
]


class WireQuantity(BaseModel):
    kind: Kind = Field(
        description=(
            "exact: the text gives a number. vague: 'some', 'a little', 'einige'. "
            "to_taste: seasoning, 'as much as needed until'. absent: no amount."
        )
    )
    value: float = Field(description="Number as written for exact, lower end of a range; 0 otherwise.")
    max_value: float = Field(description='Upper end of a range like "2–3"; 0 otherwise.')
    unit: str = Field(description='Unit exactly as written ("l", "c", "Teeglas"); "" for counted items.')
    raw: str = Field(description='The amount exactly as written, e.g. "½ l", "einige"; "" if none.')


class WireIngredient(BaseModel):
    id: str = Field(description='Short snake_case English id, unique, e.g. "red_wine".')
    name: str = Field(description="Plain English name.")
    name_original: str = Field(description="Name as written in the document.")
    quantity: WireQuantity
    preparation: str = Field(description='e.g. "sliced"; "" if none.')
    optional: bool
    is_intermediate: bool
    animal: Animal = Field(description="What of animal origin it contains; see the prompt.")
    evidence: Evidence
    page: int = Field(description="Page number, 0 if unknown.")
    quote: str = Field(description="Shortest verbatim span mentioning it; '' if not read.")
    note: str = Field(description="Reason, required when evidence is inferred; '' otherwise.")


class WireTool(BaseModel):
    id: str
    name: str
    stated: bool
    page: int
    quote: str
    note: str


class WireStep(BaseModel):
    text: str
    ingredient_ids: list[str]
    tool_ids: list[str]
    duration_raw: str = Field(description='Time as written; "" if none.')
    duration_min_minutes: float
    duration_max_minutes: float
    condition: str = Field(description='When the step applies; "" if always.')
    page: int
    quote: str


class WireServings(BaseModel):
    value: int = Field(description="0 if missing.")
    evidence: Evidence
    page: int
    quote: str
    note: str


class WireExtraction(BaseModel):
    is_recipe: bool
    recipes_in_document: int
    title: str
    language: str = Field(description="ISO 639-1 code, e.g. 'de'.")
    servings: WireServings
    ingredients: list[WireIngredient]
    tools: list[WireTool]
    steps: list[WireStep]
    warnings: list[str]
