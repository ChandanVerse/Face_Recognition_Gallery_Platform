"""
Photo upload routes with Celery task dispatch
Updated for MongoDB and local storage
"""

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from pymongo.database import Database
from typing import List
import uuid
from datetime import datetime
from bson import ObjectId

from backend.config.database import get_db
from backend.models.database import (
    PHOTOS, GALLERIES,
    create_photo_document, to_object_id, prepare_document_for_response
)
from backend.services.storage_service import StorageService
from backend.workers.celery_app import celery_app
from backend.api.auth_utils import get_current_user

router = APIRouter(prefix="/galleries", tags=["photos"])
storage_service = StorageService()


@router.post("/{gallery_id}/photos/upload")
async def upload_photos(
    gallery_id: str,
    files: List[UploadFile] = File(...),
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload photos to a gallery and trigger face recognition processing
    """
    gallery_obj_id = to_object_id(gallery_id)
    user_id = to_object_id(current_user["_id"])

    # 1. Verify gallery exists and user has access
    gallery = db[GALLERIES].find_one({"_id": gallery_obj_id})
    if not gallery:
        raise HTTPException(status_code=404, detail="Gallery not found")

    # Check ownership
    if gallery["host_user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    uploaded_photos = []

    # 2. Process each file
    for file in files:
        try:
            # Generate unique filename
            file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'webp'
            unique_filename = f"{uuid.uuid4()}.{file_extension}"
            file_path = f"galleries/{gallery_id}/photos/{unique_filename}"

            # Read file content
            file_content = await file.read()

            # 3. Upload to local storage
            storage_service.upload_file(
                file_content,
                file_path,
                content_type=file.content_type
            )

            # 4. Create photo document in database
            photo_doc = create_photo_document(
                gallery_id=gallery_obj_id,
                file_path=file_path,
                original_filename=file.filename
            )

            result = db[PHOTOS].insert_one(photo_doc)
            photo_id = result.inserted_id

            # 5. ⭐ DISPATCH TO CELERY - THIS IS THE CRITICAL PART!
            celery_app.send_task(
                'tasks.process_photo',
                args=[str(photo_id), gallery_id]
            )

            uploaded_photos.append({
                "id": str(photo_id),
                "original_filename": file.filename,
                "status": "queued"
            })

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error uploading {file.filename}: {str(e)}")

    return {
        "message": f"Successfully uploaded {len(uploaded_photos)} photo(s)",
        "photos": uploaded_photos,
        "gallery_id": gallery_id
    }


@router.get("/{gallery_id}/photos/{photo_id}/status")
async def get_photo_status(
    gallery_id: str,
    photo_id: str,
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get processing status of a photo
    """
    photo_obj_id = to_object_id(photo_id)
    gallery_obj_id = to_object_id(gallery_id)

    photo = db[PHOTOS].find_one({
        "_id": photo_obj_id,
        "gallery_id": gallery_obj_id
    })

    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    return {
        "photo_id": str(photo["_id"]),
        "status": photo.get("processing_status", "pending"),
        "face_count": photo.get("face_count", 0),
        "processed_at": photo.get("processed_at")
    }


@router.get("/{gallery_id}/photos")
async def get_gallery_photos(
    gallery_id: str,
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all photos in a gallery
    """
    gallery_obj_id = to_object_id(gallery_id)

    gallery = db[GALLERIES].find_one({"_id": gallery_obj_id})
    if not gallery:
        raise HTTPException(status_code=404, detail="Gallery not found")

    photos = list(db[PHOTOS].find({"gallery_id": gallery_obj_id}).sort("created_at", -1))

    return {
        "gallery_id": gallery_id,
        "photos": [
            {
                "id": str(photo["_id"]),
                "original_filename": photo.get("original_filename"),
                "file_path": photo.get("file_path"),
                "status": photo.get("processing_status", "pending"),
                "face_count": photo.get("face_count", 0),
                "created_at": photo.get("created_at"),
                "processed_at": photo.get("processed_at")
            }
            for photo in photos
        ]
    }
