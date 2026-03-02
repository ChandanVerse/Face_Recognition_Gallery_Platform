"""
Face Recognition Module - Standalone module for scanning and indexing known people.
"""

__version__ = "1.0.0"
__author__ = "Face Recognition Platform Team"

from .scanner import FaceScanner
from .database import KnownPeopleDB
from .matcher import FaceMatcher

__all__ = [
    "FaceScanner",
    "KnownPeopleDB",
    "FaceMatcher",
]
