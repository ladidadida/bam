"""CI pipeline generation from bam.yaml configuration."""

from .generator import generate_pipeline

__all__ = ["generate_pipeline"]
