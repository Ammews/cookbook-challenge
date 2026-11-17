"""Stage 1: ingest. Turns a PDF, an image or a text file into a Document."""

from cookbook.config import Settings
from cookbook.ingest.cache import CachedTranscriber
from cookbook.ingest.claude_transcriber import ClaudeTranscriber
from cookbook.ingest.detect import UnsupportedInputError, detect_kind
from cookbook.ingest.ingestor import Ingestor
from cookbook.ingest.readers import ImageReader, PdfReader, Reader, TextReader
from cookbook.ingest.transcriber import Transcriber, Transcription, TranscriptionError
from cookbook.models import InputKind

__all__ = [
    "CachedTranscriber",
    "ClaudeTranscriber",
    "ImageReader",
    "Ingestor",
    "PdfReader",
    "Reader",
    "TextReader",
    "Transcriber",
    "Transcription",
    "TranscriptionError",
    "UnsupportedInputError",
    "build_ingestor",
    "detect_kind",
]


def build_ingestor(settings: Settings) -> Ingestor:
    """Wire the real components together. The only place that knows about Claude."""
    claude = ClaudeTranscriber(model=settings.vision_model)
    transcriber = CachedTranscriber(
        claude,
        cache_dir=settings.cache_dir / "transcriptions",
        namespace=claude.cache_namespace,
    )
    return Ingestor(
        {
            InputKind.TEXT: TextReader(),
            InputKind.PDF: PdfReader(transcriber, settings.max_image_edge),
            InputKind.IMAGE: ImageReader(transcriber, settings.max_image_edge),
        }
    )
