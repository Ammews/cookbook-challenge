"""Runtime settings, read from environment variables."""

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_VISION_MODEL = "claude-haiku-5-5"
DEFAULT_EXTRACTION_MODEL = "claude-haiku-5-5"


@dataclass(frozen=True)
class Settings:
    vision_model: str = DEFAULT_VISION_MODEL
    extraction_model: str = DEFAULT_EXTRACTION_MODEL
    cache_dir: Path = Path(".cache")
    max_image_edge: int = 2000

    @classmethod
    def from_env(cls) -> "Settings":
        defaults = cls()
        return cls(
            vision_model=os.environ.get("COOKBOOK_VISION_MODEL") or defaults.vision_model,
            extraction_model=os.environ.get("COOKBOOK_EXTRACTION_MODEL") or defaults.extraction_model,
            cache_dir=Path(os.environ.get("COOKBOOK_CACHE_DIR") or defaults.cache_dir),
            max_image_edge=int(
                os.environ.get("COOKBOOK_MAX_IMAGE_EDGE") or defaults.max_image_edge
            ),
        )
