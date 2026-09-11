"""Pedagogical corpus package — S8.1/S8.2."""

from .schema import CorpusReviewState, PedagogicalCorpusRecord
from .text_provenance import PedagogicalText, TextSourceCategory

__all__ = ["PedagogicalCorpusRecord", "CorpusReviewState", "PedagogicalText", "TextSourceCategory"]
