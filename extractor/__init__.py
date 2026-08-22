"""Self-contained invoice extractor used as the system under test."""

from .service import extract_invoice

__all__ = ["extract_invoice"]
