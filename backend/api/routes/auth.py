"""
Authentication routes - register, login, profile management.
Updated for MongoDB and local storage
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pymongo.database import Database
from typing import List
import uuid
from bson import ObjectId

from backend.config.database import get_db
from backend.models.database import (
    USERS, PHOTOS,
    create_user_document,
    prepare_document_for_response, to_object_id
)
from backend.schemas.schemas import UserRegister, UserLogin, Token, UserResponse, ProfileStatus, ReferencePhotoResponse
from backend.api.auth_utils import hash_password, verify_password, create_access_token, get_current_user
from backend.services.storage_service import StorageService
from backend.core.storage.image_processor import ImageProcessor
from backend.workers.celery_app import celery_app

router = APIRouter()
storage = StorageService()
processor = ImageProcessor()

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: Database = Depends(get_db)):
    """Register a new user."""
    # Check if email already exists
    if db[USERS].find_one({"email": user_data.email}):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # Create user document
    user_doc = create_user_document(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        name=user_data.name
    )

    result = db[USERS].insert_one(user_doc)
    user_id = result.inserted_id

    # User profile is now embedded in users document (no separate insert needed)

    access_token = create_access_token(data={"sub": str(user_id)})
    return Token(access_token=access_token)

@router.post("/login")
async def login(credentials: UserLogin, db: Database = Depends(get_db)):
    """Login with email and password."""
    user = db[USERS].find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    access_token = create_access_token(data={"sub": str(user["_id"])})
    return Token(access_token=access_token)

@router.post("/upload-reference-photos", response_model=ProfileStatus)
async def upload_reference_photos(
    photos: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Upload reference photos to create a face recognition profile."""
    user_id = to_object_id(current_user["_id"])

    # Get user (profile embedded in users document)
    user = db[USERS].find_one({"_id": user_id})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    uploaded_count = 0
    for photo_file in photos:
        photo_data = await photo_file.read()
        if not processor.validate_image(photo_data):
            continue

        # Get file extension from original filename
        file_ext = photo_file.filename.split('.')[-1].lower()
        if file_ext not in ['jpg', 'jpeg', 'png', 'webp']:
            file_ext = 'jpg'

        file_path = f"reference/{user_id}/{uuid.uuid4()}.{file_ext}"
        storage.upload_file(photo_data, file_path)

        # Create reference photo document to embed in array
        from datetime import datetime
        ref_photo_doc = {
            "_id": ObjectId(),
            "file_path": file_path,
            "processed": False,
            "created_at": datetime.utcnow()
        }

        # Add to embedded reference_photos array
        db[USERS].update_one(
            {"_id": user_id},
            {"$push": {"reference_photos": ref_photo_doc}}
        )
        uploaded_count += 1

    # Update processing status
    db[USERS].update_one(
        {"_id": user_id},
        {"$set": {"processing_status": "processing"}}
    )

    # Trigger Celery task chain: create profile → scan galleries
    # This ensures scan only starts AFTER profile is fully created (fixes race condition)
    # Use immutable signature (.si) for scan task to ignore the result from profile task
    from celery import chain
    profile_task = celery_app.signature('tasks.create_user_profile', args=[str(user_id)])
    scan_task = celery_app.signature('tasks.scan_all_galleries_for_user', args=[str(user_id)], immutable=True)
    chain(profile_task, scan_task).apply_async()

    return ProfileStatus(
        processing_status="processing",
        reference_photo_count=user.get("reference_photo_count", 0) + uploaded_count,
        message="Reference photos uploaded. Profile creation and gallery scan in progress."
    )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user information."""
    return prepare_document_for_response(current_user)

@router.get("/my-reference-photos", response_model=List[ReferencePhotoResponse])
async def get_my_reference_photos(
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Get all reference photos for the current user with URLs."""
    user_id = to_object_id(current_user["_id"])
    print(f"[DEBUG] get_my_reference_photos called for user_id: {user_id}")

    # Get user with embedded reference_photos
    user = db[USERS].find_one({"_id": user_id})
    print(f"[DEBUG] User lookup result: {user is not None}")
    if not user:
        print(f"[DEBUG] No user found for user_id: {user_id}")
        return []

    # Access embedded reference_photos array
    reference_photos = user.get("reference_photos", [])
    print(f"[DEBUG] Found {len(reference_photos)} reference photos for user_id: {user_id}")

    result = [
        ReferencePhotoResponse(
            id=str(photo["_id"]),
            s3_key=photo["file_path"],  # Keep s3_key name for frontend compatibility
            url=storage.generate_url(photo["file_path"])
        )
        for photo in reference_photos
    ]

    print(f"[DEBUG] Returning {len(result)} photos with URLs")
    for photo_response in result:
        print(f"[DEBUG] Photo URL: {photo_response.url}")

    return result


@router.delete("/reference-photos/{photo_id}", status_code=status.HTTP_200_OK)
async def delete_reference_photo(
    photo_id: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Delete a reference photo and clean up associated data."""
    user_id = to_object_id(current_user["_id"])
    photo_obj_id = to_object_id(photo_id)

    # Find user with this reference photo in embedded array
    user = db[USERS].find_one({"_id": user_id, "reference_photos._id": photo_obj_id})

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference photo not found")

    # Find the photo in the embedded array
    photo = next((p for p in user.get("reference_photos", []) if p["_id"] == photo_obj_id), None)
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference photo not found")

    # Delete from local storage
    try:
        storage.delete_file(photo["file_path"])
    except Exception as e:
        # Log error but continue with database cleanup
        print(f"Warning: Failed to delete file from storage: {e}")

    # Remove from embedded array using $pull
    db[USERS].update_one(
        {"_id": user_id},
        {"$pull": {"reference_photos": {"_id": photo_obj_id}}}
    )

    # Get updated count
    user_updated = db[USERS].find_one({"_id": user_id})
    remaining_photos = len(user_updated.get("reference_photos", []))

    update_data = {"reference_photo_count": remaining_photos}

    # If no reference photos left, reset the profile status
    if remaining_photos == 0:
        update_data["processing_status"] = "pending"
        update_data["avg_embedding"] = None

    db[USERS].update_one(
        {"_id": user_id},
        {"$set": update_data}
    )

    return {
        "message": "Reference photo deleted successfully",
        "photo_id": photo_id,
        "remaining_photos": remaining_photos
    }


@router.post("/reupload-reference-photos", response_model=ProfileStatus)
async def reupload_reference_photos(
    photos: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Re-upload reference photos: Clear old photos, delete embeddings, and create fresh profile.
    This triggers a complete re-scan of all galleries.
    """
    user_id = to_object_id(current_user["_id"])

    # Get user
    user = db[USERS].find_one({"_id": user_id})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # 1. Get all old reference photos from embedded array
    old_photos = user.get("reference_photos", [])

    # 2. Delete old files from storage
    for old_photo in old_photos:
        try:
            storage.delete_file(old_photo["file_path"])
        except Exception as e:
            print(f"Warning: Failed to delete file: {e}")

    # 3. Clear embedded reference_photos array
    db[USERS].update_one(
        {"_id": user_id},
        {"$set": {"reference_photos": []}}
    )

    # 4. Delete old Pinecone embedding
    try:
        from backend.services.face_service import FaceService
        face_service = FaceService()
        face_service._db.delete_vectors([f"user:{user_id}"])
        print(f"✓ Deleted Pinecone embedding for user:{user_id}")
    except Exception as e:
        print(f"Warning: Failed to delete Pinecone embedding: {e}")

    # 5. Clear old user-photo associations from photos.matched_users arrays
    db[PHOTOS].update_many(
        {"matched_users.user_id": user_id},
        {"$pull": {"matched_users": {"user_id": user_id}}}
    )
    print(f"✓ Cleared old photo associations for user {user_id}")

    # 6. Upload new reference photos
    uploaded_count = 0
    for photo_file in photos:
        photo_data = await photo_file.read()
        if not processor.validate_image(photo_data):
            continue

        # Get file extension from original filename
        file_ext = photo_file.filename.split('.')[-1].lower()
        if file_ext not in ['jpg', 'jpeg', 'png', 'webp']:
            file_ext = 'jpg'

        file_path = f"reference/{user_id}/{uuid.uuid4()}.{file_ext}"
        storage.upload_file(photo_data, file_path)

        # Create reference photo document for embedded array
        from datetime import datetime
        ref_photo_doc = {
            "_id": ObjectId(),
            "file_path": file_path,
            "processed": False,
            "created_at": datetime.utcnow()
        }

        # Add to embedded array
        db[USERS].update_one(
            {"_id": user_id},
            {"$push": {"reference_photos": ref_photo_doc}}
        )
        uploaded_count += 1

    # 7. Update profile status
    db[USERS].update_one(
        {"_id": user_id},
        {"$set": {
            "processing_status": "processing",
            "avg_embedding": None,
            "reference_photo_count": 0
        }}
    )

    # 8. Trigger Celery task chain: create profile → scan galleries
    # This ensures scan only starts AFTER profile is fully recreated (fixes race condition)
    # Use immutable signature for scan task to ignore the result from profile task
    from celery import chain
    profile_task = celery_app.signature('tasks.create_user_profile', args=[str(user_id)])
    scan_task = celery_app.signature('tasks.scan_all_galleries_for_user', args=[str(user_id)], immutable=True)
    chain(profile_task, scan_task).apply_async()

    return ProfileStatus(
        processing_status="processing",
        reference_photo_count=uploaded_count,
        message=f"Re-uploaded {uploaded_count} reference photos. Profile recreation and gallery re-scan in progress."
    )


@router.post("/trigger-gallery-scan", status_code=status.HTTP_200_OK)
async def trigger_gallery_scan(
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Manually trigger retroactive gallery scan for current user.
    Useful when face matching didn't work during initial upload or for re-scanning all galleries.

    This endpoint clears all previous photo associations and then scans all existing
    gallery photos to find faces matching the user's current profile.
    """
    user_id = to_object_id(current_user["_id"])

    # Check if user profile exists and is ready
    user = db[USERS].find_one({"_id": user_id})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Please upload reference photos first."
        )

    if not user.get("avg_embedding"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile not ready. Your reference photos are still being processed. Please wait a moment and try again."
        )

    if user.get("processing_status") != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Profile is currently {user['processing_status']}. Please wait for processing to complete."
        )

    # Clear old user-photo associations from photos.matched_users arrays
    result = db[PHOTOS].update_many(
        {"matched_users.user_id": user_id},
        {"$pull": {"matched_users": {"user_id": user_id}}}
    )
    deleted_count = result.modified_count
    print(f"✓ Cleared photo associations from {deleted_count} photos for user {user_id}")

    # Trigger retroactive scan with fresh associations
    celery_app.send_task('tasks.scan_all_galleries_for_user', args=[str(user_id)])

    return {
        "message": "Gallery scan triggered successfully",
        "user_id": str(user_id),
        "cleared_associations": deleted_count,
        "status": "Previous results cleared. Scan task queued. Check back in a few moments for fresh results."
    }
