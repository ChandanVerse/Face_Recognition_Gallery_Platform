"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List


# ============ Auth Schemas ============
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=1, max_length=255)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str  # MongoDB ObjectId as string
    email: str
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Gallery Schemas ============
class GalleryCreate(BaseModel):
    name: Optional[str] = None


class GalleryResponse(BaseModel):
    id: str  # MongoDB ObjectId as string
    host_user_id: str  # Owner of the gallery
    share_token: str
    name: Optional[str]
    processing_status: str
    total_photos: int
    processed_photos: int
    created_at: datetime

    class Config:
        from_attributes = True


class GalleryUploadResponse(BaseModel):
    gallery: GalleryResponse
    upload_url: str
    message: str


# ============ Photo Schemas ============
class TaggedPerson(BaseModel):
    """Person tagged in a photo from known_faces_matches"""
    person_name: str
    person_id: Optional[str] = None  # MongoDB ObjectId as string
    confidence: float
    linkedin_profile: Optional[str] = None


class PhotoResponse(BaseModel):
    id: str  # MongoDB ObjectId as string
    gallery_id: str  # MongoDB ObjectId as string
    file_path: str  # Changed from s3_key to file_path
    original_filename: Optional[str]
    processing_status: str
    face_count: int
    created_at: datetime
    url: Optional[str] = None  # Static URL
    tagged_people: List[TaggedPerson] = []  # People found in this photo

    class Config:
        from_attributes = True


class FaceAnnotation(BaseModel):
    """Face bounding box and metadata"""
    face_id: str  # MongoDB ObjectId as string
    bbox: dict  # {x1, y1, x2, y2}
    user_name: Optional[str] = None
    confidence: Optional[float] = None


class PhotoWithFaces(BaseModel):
    """Photo with face annotations"""
    photo: PhotoResponse
    faces: List[FaceAnnotation]


# ============ User Profile Schemas ============
class ProfileStatus(BaseModel):
    processing_status: str
    reference_photo_count: int
    message: str


# ============ Search Results ============
class UserPhotoMatch(BaseModel):
    photo_id: str  # MongoDB ObjectId as string
    confidence: float
    photo: PhotoResponse


class MyPhotosResponse(BaseModel):
    total_matches: int
    photos: List[PhotoResponse]

# ADD THIS NEW CLASS
class ReferencePhotoResponse(BaseModel):
    id: str  # MongoDB ObjectId as string
    s3_key: str  # Keep for frontend compatibility (actually stores file_path)
    url: str  # This will be the static URL

    class Config:
        from_attributes = True


# ============ Debug/Analysis Schemas ============
class FaceDetail(BaseModel):
    """Detailed face information with match data"""
    face_id: str  # MongoDB ObjectId as string
    bbox: dict  # {x1, y1, x2, y2}
    matched_user_id: Optional[str] = None  # MongoDB ObjectId as string
    matched_user_name: Optional[str] = None
    confidence_score: Optional[float] = None
    pinecone_id: str


class PhotoWithConfidence(BaseModel):
    """Photo with confidence score for user match"""
    id: str  # MongoDB ObjectId as string
    gallery_id: str  # MongoDB ObjectId as string
    file_path: str  # Changed from s3_key to file_path
    original_filename: Optional[str]
    processing_status: str
    face_count: int
    created_at: datetime
    url: Optional[str] = None
    confidence: Optional[float] = None  # User's confidence score for this photo
    matched_faces: List[FaceDetail] = []  # All faces that matched the user
    tagged_people: List[TaggedPerson] = []  # All known people tagged in this photo


class PhotoDebugInfo(BaseModel):
    """Complete debug information for a photo"""
    photo_id: str  # MongoDB ObjectId as string
    total_faces_detected: int
    faces: List[FaceDetail]
    processing_status: str