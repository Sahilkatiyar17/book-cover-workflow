"""
Centralized static constants for the book-cover-workflow project.
Nothing secret or environment-specific goes here — that belongs in config.py.
Change values here, not inline in services/graph code.
"""


class BookDimensions:
    """Standard print book cover dimensions, in inches (width x height)."""
    PRESETS = {
        "5x8": (5, 8),
        "5.5x8.5": (5.5, 8.5),
        "6x9": (6, 9),
        "7x10": (7, 10),
        "8.5x11": (8.5, 11),
    }
    DEFAULT_PRESET = "6x9"
    DPI = 300  # standard print resolution


class ImageSearchConfig:
    """Tunables for the image search + ranking step."""
    DEFAULT_RESULTS_PER_QUERY = 10
    MAX_RESULTS_PER_QUERY = 20
    SUPPORTED_PROVIDERS = ("unsplash", "pexels")
    DEFAULT_PROVIDER = "unsplash"


class GenerationConfig:
    """Tunables for the image generation step."""
    MAX_REFERENCE_IMAGES = 5
    DEFAULT_MODEL = "gemini"  # matches settings.gemini_api_key usage
    FALLBACK_MODEL = "gpt-image"
    GENERATION_TIMEOUT_SECONDS = 60
    MAX_RETRIES = 3
    RETRY_BACKOFF_SECONDS = 2


class GraphConfig:
    """Tunables for LangGraph execution and checkpointing."""
    CHECKPOINT_DB_PATH = "storage/checkpoints.db"
    RAW_IMAGE_DIR = "storage/raw_images"
    GENERATED_COVER_DIR = "storage/generated_covers"


class FeedbackBranch:
    """Branch labels used in edges.py routing logic — keeps string literals in one place."""
    NO_FEEDBACK = "no_feedback"
    TEXT_FEEDBACK = "text_feedback"
    USER_IMAGE_UPLOAD = "user_image_upload"
    TEXT_AND_IMAGE = "text_and_image"