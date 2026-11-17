"""Load evaluation cases from `evals/cases/<id>/case.yaml`."""

from pathlib import Path

import yaml

from cookbook.evaluation.spec import CaseSpec
from cookbook.models.base import DomainModel

CASE_FILE = "case.yaml"


class Case(DomainModel):
    spec: CaseSpec
    folder: Path

    @property
    def input_path(self) -> Path:
        return (self.folder / self.spec.input).resolve()

    @property
    def input_available(self) -> bool:
        """False when a local-only input (not in the repo) has not been put in place."""
        return self.input_path.is_file()

    @property
    def reference_transcription(self) -> str | None:
        if self.spec.reference_transcription is None:
            return None
        return (self.folder / self.spec.reference_transcription).read_text(encoding="utf-8")


def load_case(folder: Path) -> Case:
    data = yaml.safe_load((folder / CASE_FILE).read_text(encoding="utf-8"))
    spec = CaseSpec.model_validate(data)
    if spec.id != folder.name:
        raise ValueError(f"case id '{spec.id}' does not match its folder '{folder.name}'")
    return Case(spec=spec, folder=folder)


def load_cases(root: Path) -> list[Case]:
    return [load_case(folder) for folder in sorted(root.iterdir()) if (folder / CASE_FILE).is_file()]
