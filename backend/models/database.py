"""
MongoDB document schemas and helper functions
Replaces SQLAlchemy models with simple MongoDB document structures
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from bson import ObjectId


# Collection names
USERS = "users"
GALLERIES = "galleries"
PHOTOS = "photos"


def create_user_document(email: str, password_hash: str, name: str) -> Dict[str, Any]:
    """Create a user document with embedded profile and reference photos"""
    return {
        "email": email,
        "password_hash": password_hash,
        "name": name,
        "created_at": datetime.utcnow(),
        # Profile fields (merged from user_profiles)
        "avg_embedding": None,
        "reference_photo_count": 0,
        "processing_status": "pending",
        "profile_updated_at": datetime.utcnow(),
        # Reference photos array (merged from reference_photos collection)
        "reference_photos": []
    }


def create_gallery_document(host_user_id: ObjectId, share_token: str, name: Optional[str] = None, total_photos: int = 0) -> Dict[str, Any]:
    """Create a gallery document"""
    return {
        "host_user_id": host_user_id,
        "share_token": share_token,
        "name": name,
        "processing_status": "pending",  # pending, processing, completed
        "total_photos": total_photos,
        "processed_photos": 0,
        "created_at": datetime.utcnow()
    }


def create_photo_document(gallery_id: ObjectId, file_path: str, original_filename: Optional[str] = None) -> Dict[str, Any]:
    """Create a photo document with embedded faces, matched_users, and tagged_people arrays"""
    return {
        "gallery_id": gallery_id,
        "file_path": file_path,
        "original_filename": original_filename,
        "processing_status": "pending",  # pending, processing, completed, failed
        "face_count": 0,
        "created_at": datetime.utcnow(),
        "processed_at": None,
        # Embedded arrays
        "faces": [],  # Embedded from faces collection
        "matched_users": [],  # Embedded from user_photo_associations
        "tagged_people": []  # Embedded from known_faces_matches
    }


# Helper functions for MongoDB ObjectId conversion
def to_object_id(id_value: Any) -> ObjectId:
    """Convert string or int to ObjectId"""
    if isinstance(id_value, ObjectId):
        return id_value
    elif isinstance(id_value, str):
        return ObjectId(id_value)
    elif isinstance(id_value, int):
        # For backward compatibility with integer IDs
        # We'll use a simple conversion - pad to 24 chars
        return ObjectId(str(id_value).zfill(24))
    else:
        raise ValueError(f"Cannot convert {type(id_value)} to ObjectId")


def from_object_id(obj_id: ObjectId) -> str:
    """Convert ObjectId to string"""
    return str(obj_id)


def prepare_document_for_response(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Convert MongoDB document for API response (ObjectId to string)"""
    if doc is None:
        return None

    result = dict(doc)

    # Convert _id to id and make it a string
    if "_id" in result:
        result["id"] = str(result.pop("_id"))

    # Convert any other ObjectId fields to strings
    for key, value in result.items():
        if isinstance(value, ObjectId):
            result[key] = str(value)
        elif isinstance(value, datetime):
            result[key] = value.isoformat()

    return result


__all__ = [
    "USERS",
    "GALLERIES",
    "PHOTOS",
    "create_user_document",
    "create_gallery_document",
    "create_photo_document",
    "to_object_id",
    "from_object_id",
    "prepare_document_for_response"
]
