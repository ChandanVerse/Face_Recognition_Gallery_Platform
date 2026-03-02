"""
Gallery management routes - create, upload, view
Updated for MongoDB and local storage
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pymongo.database import Database
from typing import List
import uuid
from bson import ObjectId
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from backend.config.database import get_db
from backend.models.database import (
    GALLERIES, PHOTOS, USERS,
    create_gallery_document, create_photo_document,
    prepare_document_for_response, to_object_id
)
from backend.schemas.schemas import (
    GalleryResponse, GalleryUploadResponse, PhotoResponse, PhotoWithFaces,
    FaceAnnotation, PhotoWithConfidence, PhotoDebugInfo, FaceDetail, TaggedPerson
)
from backend.api.auth_utils import get_current_user
from backend.services.storage_service import StorageService
from backend.core.storage.image_processor import ImageProcessor
from backend.workers.celery_app import celery_app

router = APIRouter()
storage = StorageService()
processor = ImageProcessor()

# Thread pool for CPU-intensive image processing
# Limit to 6 threads to avoid overloading the system
thread_pool = ThreadPoolExecutor(max_workers=6)


async def process_single_photo(photo_file: UploadFile, gallery_obj_id: ObjectId, share_token: str, gallery_id: str, db: Database):
    """
    Process a single photo: read, validate, store, and queue for face detection

    Returns: tuple (success: bool, error_msg: str|None)
    """
    try:
        # Read file data
        photo_data = await photo_file.read()

        # Validate image
        if not processor.validate_image(photo_data):
            return (False, f"Invalid image: {photo_file.filename}")

        # Get file extension from original filename
        file_ext = photo_file.filename.split('.')[-1].lower()
        if file_ext not in ['jpg', 'jpeg', 'png', 'webp']:
            file_ext = 'jpg'

        # Generate unique file path with original extension
        file_path = f"galleries/{share_token}/{uuid.uuid4()}.{file_ext}"

        # Save to storage (offload to thread pool)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            thread_pool,
            partial(storage.upload_file, photo_data, file_path)
        )

        # Create photo document in MongoDB
        photo_doc = create_photo_document(
            gallery_id=gallery_obj_id,
            file_path=file_path,
            original_filename=photo_file.filename
        )

        photo_result = db[PHOTOS].insert_one(photo_doc)
        photo_id = photo_result.inserted_id

        # Queue Celery task for face detection
        celery_app.send_task(
            'tasks.process_photo',
            args=[str(photo_id), str(gallery_id)]
        )

        return (True, None)

    except Exception as e:
        return (False, f"Error processing {photo_file.filename}: {str(e)}")


@router.get("/my-galleries", response_model=List[GalleryResponse])
async def get_my_galleries(
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Get all galleries hosted by the current authenticated user with accurate photo counts."""
    user_id = to_object_id(current_user["_id"])
    galleries = list(db[GALLERIES].find({"host_user_id": user_id}).sort("created_at", -1))

    # Fix photo counts by querying actual photo count from PHOTOS collection
    # This ensures the count is always accurate and in sync with the database
    result = []
    for gallery in galleries:
        actual_photo_count = db[PHOTOS].count_documents({"gallery_id": gallery["_id"]})
        gallery["total_photos"] = actual_photo_count  # Override with accurate count
        print(f"[DEBUG] Gallery '{gallery.get('name', 'Untitled')}' - DB count: {actual_photo_count}")
        result.append(prepare_document_for_response(gallery))

    return result

@router.post("/create", response_model=GalleryResponse, status_code=status.HTTP_201_CREATED)
async def create_empty_gallery(
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Create an empty gallery (photos to be added later via batch upload)."""
    user_id = to_object_id(current_user["_id"])
    share_token = str(uuid.uuid4())

    # Create gallery document with 0 photos
    gallery_doc = create_gallery_document(
        host_user_id=user_id,
        share_token=share_token,
        total_photos=0
    )

    result = db[GALLERIES].insert_one(gallery_doc)
    gallery_id = result.inserted_id

    # Get the created gallery
    gallery = db[GALLERIES].find_one({"_id": gallery_id})

    return prepare_document_for_response(gallery)

@router.post("/{gallery_id}/add-photos", status_code=status.HTTP_200_OK)
async def add_photos_to_gallery(
    gallery_id: str,
    photos: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Add more photos to an existing gallery with parallel processing.

    Optimizations:
    - Process up to 6 photos concurrently
    - Offload CPU-intensive compression to thread pool
    - Non-blocking I/O operations
    """
    if not photos or len(photos) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one photo required"
        )

    user_id = to_object_id(current_user["_id"])
    gallery_obj_id = to_object_id(gallery_id)

    # Get gallery and verify ownership
    gallery = db[GALLERIES].find_one({"_id": gallery_obj_id})
    if not gallery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gallery not found")

    if gallery["host_user_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    share_token = gallery["share_token"]

    # Process photos in parallel with concurrency limit (6 at a time)
    semaphore = asyncio.Semaphore(6)

    async def process_with_semaphore(photo):
        async with semaphore:
            return await process_single_photo(photo, gallery_obj_id, share_token, gallery_id, db)

    # Process all photos concurrently
    results = await asyncio.gather(
        *[process_with_semaphore(photo) for photo in photos],
        return_exceptions=True
    )

    # Count successes and failures
    uploaded_count = sum(1 for success, _ in results if success)
    failed_count = len(results) - uploaded_count

    # Log failures
    for success, error_msg in results:
        if not success and error_msg:
            print(f"❌ {error_msg}")

    # Update gallery total_photos count
    new_total = gallery["total_photos"] + uploaded_count
    db[GALLERIES].update_one(
        {"_id": gallery_obj_id},
        {"$set": {"total_photos": new_total, "processing_status": "processing"}}
    )

    print(f"✅ Batch complete: {uploaded_count} uploaded, {failed_count} failed")

    # Queue tagging task to run after photo processing completes
    # This will tag known people from the known_faces directory
    if uploaded_count > 0:
        celery_app.send_task(
            'tasks.tag_known_people_in_gallery',
            args=[gallery_id]
        )

    return {
        "message": f"Added {uploaded_count} photos to gallery",
        "uploaded_count": uploaded_count,
        "failed_count": failed_count,
        "gallery_id": gallery_id
    }

@router.post("/upload", response_model=GalleryUploadResponse, status_code=status.HTTP_201_CREATED)
async def create_gallery_and_upload(
    photos: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Create a new gallery and upload photos."""
    if not photos or len(photos) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one photo required"
        )

    user_id = to_object_id(current_user["_id"])
    share_token = str(uuid.uuid4())

    # Create gallery document
    gallery_doc = create_gallery_document(
        host_user_id=user_id,
        share_token=share_token,
        total_photos=len(photos)
    )
    # Set to processing immediately since we're uploading photos
    gallery_doc["processing_status"] = "processing"

    result = db[GALLERIES].insert_one(gallery_doc)
    gallery_id = result.inserted_id

    for photo_file in photos:
        try:
            photo_data = await photo_file.read()

            if not processor.validate_image(photo_data):
                continue

            # Get file extension from original filename
            file_ext = photo_file.filename.split('.')[-1].lower()
            if file_ext not in ['jpg', 'jpeg', 'png', 'webp']:
                file_ext = 'jpg'

            file_path = f"galleries/{share_token}/{uuid.uuid4()}.{file_ext}"
            storage.upload_file(photo_data, file_path)

            # Create photo document
            photo_doc = create_photo_document(
                gallery_id=gallery_id,
                file_path=file_path,
                original_filename=photo_file.filename
            )

            photo_result = db[PHOTOS].insert_one(photo_doc)
            photo_id = photo_result.inserted_id

            celery_app.send_task(
                'tasks.process_photo',
                args=[str(photo_id), str(gallery_id)]
            )
        except Exception as e:
            print(f"Error uploading photo {photo_file.filename}: {e}")
            continue

    # Get the created gallery for response
    gallery = db[GALLERIES].find_one({"_id": gallery_id})
    upload_url = f"/gallery/{share_token}"

    # Queue tagging task to run after photo processing completes
    # This will tag known people from the known_faces directory
    celery_app.send_task(
        'tasks.tag_known_people_in_gallery',
        args=[str(gallery_id)]
    )

    return GalleryUploadResponse(
        gallery=prepare_document_for_response(gallery),
        upload_url=upload_url,
        message=f"Gallery created with {len(photos)} photos. Processing started."
    )

@router.get("/{share_token}", response_model=GalleryResponse)
async def get_gallery_by_token(share_token: str, db: Database = Depends(get_db)):
    """Get gallery details by share token (public endpoint)."""
    gallery = db[GALLERIES].find_one({"share_token": share_token})
    if not gallery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gallery not found")
    return prepare_document_for_response(gallery)

@router.get("/{share_token}/all-photos")
async def get_all_gallery_photos(
    share_token: str,
    page: int = 1,
    page_size: int = 50,
    db: Database = Depends(get_db)
):
    """
    Get paginated photos in a gallery with presigned URLs (public endpoint).

    Args:
        share_token: Gallery share token
        page: Page number (starts from 1)
        page_size: Number of photos per page (default: 50, max: 100)

    Returns:
        Dictionary with photos list, pagination info, and total count
    """
    gallery = db[GALLERIES].find_one({"share_token": share_token})
    if not gallery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gallery not found")

    # Validate and limit page_size
    page_size = min(max(1, page_size), 100)  # Between 1 and 100
    page = max(1, page)  # At least page 1

    # Calculate skip and limit
    skip = (page - 1) * page_size

    # Get total count
    total_photos = db[PHOTOS].count_documents({"gallery_id": gallery["_id"]})

    # Get paginated photos
    photos = list(db[PHOTOS].find({"gallery_id": gallery["_id"]})
                  .sort("created_at", -1)
                  .skip(skip)
                  .limit(page_size))

    # Calculate pagination metadata
    total_pages = (total_photos + page_size - 1) // page_size if total_photos > 0 else 1

    # Build response with tagged_people
    photos_response = []
    for photo in photos:
        photo_dict = prepare_document_for_response(photo)

        # Access embedded tagged_people array
        tagged_people_array = photo.get("tagged_people", [])
        tagged_people = [
            TaggedPerson(
                person_name=match["person_name"],
                person_id=str(match["person_id"]),
                confidence=match["confidence"],
                linkedin_profile=match.get("linkedin_profile")
            )
            for match in tagged_people_array
        ]

        photos_response.append(
            PhotoResponse(
                **photo_dict,
                url=storage.generate_url(photo["file_path"]),
                tagged_people=tagged_people
            )
        )

    return {
        "photos": photos_response,
        "pagination": {
            "current_page": page,
            "page_size": page_size,
            "total_photos": total_photos,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1
        }
    }

@router.get("/{share_token}/my-photos", response_model=List[PhotoResponse])
async def get_my_photos_in_gallery(
    share_token: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Get only photos where the authenticated user appears."""
    user_id = to_object_id(current_user["_id"])

    gallery = db[GALLERIES].find_one({"share_token": share_token})
    if not gallery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gallery not found")

    # Use multikey index to find photos where user appears (matched_users.user_id)
    photos = list(db[PHOTOS].find({
        "gallery_id": gallery["_id"],
        "matched_users.user_id": user_id
    }))

    if not photos:
        return []

    # Build response with embedded tagged_people
    return [
        PhotoResponse(
            **prepare_document_for_response(photo),
            url=storage.generate_url(photo["file_path"]),
            tagged_people=[
                TaggedPerson(
                    person_name=match["person_name"],
                    person_id=str(match["person_id"]),
                    confidence=match["confidence"],
                    linkedin_profile=match.get("linkedin_profile")
                )
                for match in photo.get("tagged_people", [])
            ]
        )
        for photo in photos
    ]

@router.get("/{share_token}/status")
async def get_gallery_status(share_token: str, db: Database = Depends(get_db)):
    """Get processing status of a gallery."""
    gallery = db[GALLERIES].find_one({"share_token": share_token})
    if not gallery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gallery not found")

    processed_count = db[PHOTOS].count_documents({
        "gallery_id": gallery["_id"],
        "processing_status": "completed"
    })
    total_count = gallery["total_photos"]
    progress = (processed_count / total_count * 100) if total_count > 0 else 0

    # Auto-update gallery status to completed when all photos are processed
    current_status = gallery["processing_status"]
    if total_count > 0 and processed_count >= total_count and current_status != "completed":
        db[GALLERIES].update_one(
            {"_id": gallery["_id"]},
            {"$set": {"processing_status": "completed", "processed_photos": processed_count}}
        )
        current_status = "completed"
    elif processed_count < total_count and current_status == "pending":
        # Update to processing if photos are being processed
        db[GALLERIES].update_one(
            {"_id": gallery["_id"]},
            {"$set": {"processing_status": "processing", "processed_photos": processed_count}}
        )
        current_status = "processing"
    else:
        # Just update processed_photos count
        db[GALLERIES].update_one(
            {"_id": gallery["_id"]},
            {"$set": {"processed_photos": processed_count}}
        )

    return {
        "gallery_id": str(gallery["_id"]),
        "processing_status": current_status,
        "total_photos": total_count,
        "processed_photos": processed_count,
        "progress_percentage": round(progress, 2)
    }


@router.get("/{share_token}/my-photos-with-confidence")
async def get_my_photos_with_confidence(
    share_token: str,
    page: int = 1,
    page_size: int = 50,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Get paginated photos where user appears WITH confidence scores for each face.

    Args:
        share_token: Gallery share token
        page: Page number (starts from 1)
        page_size: Number of photos per page (default: 50, max: 100)
        current_user: Authenticated user
        db: Database connection

    Returns:
        Dictionary with photos list, pagination info, and total count
    """
    user_id = to_object_id(current_user["_id"])

    gallery = db[GALLERIES].find_one({"share_token": share_token})
    if not gallery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gallery not found")

    # Validate and limit page_size
    page_size = min(max(1, page_size), 100)  # Between 1 and 100
    page = max(1, page)  # At least page 1

    # Get all photo associations for this user in this gallery
    # First get all photos in this gallery
    gallery_photos = list(db[PHOTOS].find({"gallery_id": gallery["_id"]}))
    gallery_photo_ids = [photo["_id"] for photo in gallery_photos]

    # Query photos with matched_users array using multikey index
    photos = list(db[PHOTOS].find({
        "gallery_id": gallery["_id"],
        "matched_users.user_id": user_id,
        "_id": {"$in": gallery_photo_ids}
    }))

    if not photos:
        return {
            "photos": [],
            "pagination": {
                "current_page": 1,
                "page_size": page_size,
                "total_photos": 0,
                "total_pages": 0,
                "has_next": False,
                "has_previous": False
            }
        }

    # Build photo map with face details from embedded arrays
    photo_map = {}
    for photo in photos:
        photo_id = photo["_id"]

        # Get all matched_users entries for this user
        user_matches = [m for m in photo.get("matched_users", []) if m["user_id"] == user_id]

        if not user_matches:
            continue

        # Find highest confidence match for this photo
        max_confidence = max(m["confidence"] for m in user_matches)

        # Build face details from embedded faces array
        faces_list = []
        for match in user_matches:
            face_index = match.get("face_index")
            if face_index is not None and face_index < len(photo.get("faces", [])):
                face = photo["faces"][face_index]
                faces_list.append(FaceDetail(
                    face_id=f"{photo_id}_{face_index}",  # Synthetic ID
                    bbox={
                        'x1': face["bbox_x1"],
                        'y1': face["bbox_y1"],
                        'x2': face["bbox_x2"],
                        'y2': face["bbox_y2"]
                    },
                    matched_user_id=str(user_id),
                    matched_user_name=current_user["name"],
                    confidence_score=match["confidence"],
                    pinecone_id=face["pinecone_id"]
                ))

        photo_map[photo_id] = {
            'photo': photo,
            'max_confidence': max_confidence,
            'faces': faces_list
        }

    # Build response
    all_photos = []
    for photo_data in photo_map.values():
        photo = photo_data['photo']

        # Access embedded tagged_people array
        tagged_people_array = photo.get("tagged_people", [])
        tagged_people = [
            TaggedPerson(
                person_name=match["person_name"],
                person_id=str(match["person_id"]),
                confidence=match["confidence"],
                linkedin_profile=match.get("linkedin_profile")
            )
            for match in tagged_people_array
        ]

        all_photos.append(PhotoWithConfidence(
            **prepare_document_for_response(photo),
            url=storage.generate_url(photo["file_path"]),
            confidence=photo_data['max_confidence'],
            matched_faces=photo_data['faces'],
            tagged_people=tagged_people
        ))

    # Sort by confidence descending
    all_photos.sort(key=lambda x: x.confidence, reverse=True)

    # Apply pagination
    total_photos = len(all_photos)
    total_pages = (total_photos + page_size - 1) // page_size if total_photos > 0 else 1
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_photos = all_photos[start_idx:end_idx]

    return {
        "photos": paginated_photos,
        "pagination": {
            "current_page": page,
            "page_size": page_size,
            "total_photos": total_photos,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1
        }
    }


@router.get("/{share_token}/photos/{photo_id}/debug", response_model=PhotoDebugInfo)
async def get_photo_debug_info(
    share_token: str,
    photo_id: str,
    db: Database = Depends(get_db)
):
    """Get detailed debug information for a specific photo showing ALL detected faces and their matches."""
    gallery = db[GALLERIES].find_one({"share_token": share_token})
    if not gallery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gallery not found")

    photo_obj_id = to_object_id(photo_id)
    photo = db[PHOTOS].find_one({"_id": photo_obj_id, "gallery_id": gallery["_id"]})
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found")

    # Get all faces from embedded array
    faces = photo.get("faces", [])

    # Get all matched_users from embedded array
    matched_users_array = photo.get("matched_users", [])

    face_details = []
    for face_index, face in enumerate(faces):
        # Find all user matches for this face
        matches_for_face = [m for m in matched_users_array if m.get("face_index") == face_index]

        matched_user = None
        confidence = None
        if matches_for_face:
            # Get first match (in case multiple users matched)
            match = matches_for_face[0]
            matched_user = db[USERS].find_one({"_id": match["user_id"]})
            confidence = match["confidence"]

        face_details.append(FaceDetail(
            face_id=f"{photo_obj_id}_{face_index}",  # Synthetic ID
            bbox={
                'x1': face["bbox_x1"],
                'y1': face["bbox_y1"],
                'x2': face["bbox_x2"],
                'y2': face["bbox_y2"]
            },
            matched_user_id=str(matched_user["_id"]) if matched_user else None,
            matched_user_name=matched_user["name"] if matched_user else None,
            confidence_score=confidence,
            pinecone_id=face["pinecone_id"]
        ))

    return PhotoDebugInfo(
        photo_id=str(photo["_id"]),
        total_faces_detected=len(faces),
        faces=face_details,
        processing_status=photo["processing_status"]
    )


@router.get("/{share_token}/debug/all-photos", response_model=List[PhotoDebugInfo])
async def get_all_photos_debug(
    share_token: str,
    db: Database = Depends(get_db)
):
    """Get debug info for ALL photos in gallery - shows every face and match."""
    gallery = db[GALLERIES].find_one({"share_token": share_token})
    if not gallery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gallery not found")

    photos = list(db[PHOTOS].find({"gallery_id": gallery["_id"]}))

    result = []
    for photo in photos:
        # Get faces from embedded array
        faces = photo.get("faces", [])

        # Get matched_users from embedded array
        matched_users_array = photo.get("matched_users", [])

        face_details = []
        for face_index, face in enumerate(faces):
            # Find all user matches for this face
            matches_for_face = [m for m in matched_users_array if m.get("face_index") == face_index]

            matched_user = None
            confidence = None
            if matches_for_face:
                # Get first match (in case multiple users matched)
                match = matches_for_face[0]
                matched_user = db[USERS].find_one({"_id": match["user_id"]})
                confidence = match["confidence"]

            face_details.append(FaceDetail(
                face_id=f"{photo['_id']}_{face_index}",  # Synthetic ID
                bbox={
                    'x1': face["bbox_x1"],
                    'y1': face["bbox_y1"],
                    'x2': face["bbox_x2"],
                    'y2': face["bbox_y2"]
                },
                matched_user_id=str(matched_user["_id"]) if matched_user else None,
                matched_user_name=matched_user["name"] if matched_user else None,
                confidence_score=confidence,
                pinecone_id=face["pinecone_id"]
            ))

        result.append(PhotoDebugInfo(
            photo_id=str(photo["_id"]),
            total_faces_detected=len(faces),
            faces=face_details,
            processing_status=photo["processing_status"]
        ))

    return result


@router.post("/{share_token}/tag-known-people", status_code=status.HTTP_200_OK)
async def tag_known_people_in_gallery(
    share_token: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Manually trigger tagging of known people in a gallery.
    Only gallery owner can trigger this.
    """
    user_id = to_object_id(current_user["_id"])

    # Get the gallery and verify ownership
    gallery = db[GALLERIES].find_one({"share_token": share_token})
    if not gallery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gallery not found")

    # Verify the current user is the gallery host
    if gallery["host_user_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to tag photos in this gallery")

    # Queue Celery task to tag known people
    task = celery_app.send_task(
        'tasks.tag_known_people_in_gallery',
        args=[str(gallery["_id"])]
    )

    return {
        "message": "Tagging known people in progress",
        "gallery_id": str(gallery["_id"]),
        "task_id": task.id,
        "status": "processing"
    }


@router.delete("/{share_token}/photos/{photo_id}", status_code=status.HTTP_200_OK)
async def delete_gallery_photo(
    share_token: str,
    photo_id: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Delete a photo from a gallery and clean up all associated data."""
    user_id = to_object_id(current_user["_id"])

    # Get the gallery and verify ownership
    gallery = db[GALLERIES].find_one({"share_token": share_token})
    if not gallery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gallery not found")

    # Verify the current user is the gallery host
    if gallery["host_user_id"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete photos from this gallery")

    # Get the photo and verify it belongs to this gallery
    photo_obj_id = to_object_id(photo_id)
    photo = db[PHOTOS].find_one({"_id": photo_obj_id, "gallery_id": gallery["_id"]})
    if not photo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Photo not found in this gallery")

    # Get all faces from embedded array to delete from Pinecone
    faces = photo.get("faces", [])
    pinecone_ids = [face["pinecone_id"] for face in faces]

    # Delete from Pinecone if there are faces
    if pinecone_ids:
        try:
            from backend.services.face_service import FaceService
            face_service = FaceService()
            face_service._db.delete_vectors(pinecone_ids)
        except Exception as e:
            print(f"Warning: Failed to delete vectors from Pinecone: {e}")

    # Delete from storage
    try:
        storage.delete_file(photo["file_path"])
    except Exception as e:
        print(f"Warning: Failed to delete file from storage: {e}")

    # Delete the photo (faces and associations are embedded, so no separate cleanup needed)
    db[PHOTOS].delete_one({"_id": photo_obj_id})

    # Update gallery photo count
    new_total = max(0, gallery["total_photos"] - 1)
    db[GALLERIES].update_one(
        {"_id": gallery["_id"]},
        {"$set": {"total_photos": new_total}}
    )

    return {
        "message": "Photo deleted successfully",
        "photo_id": photo_id,
        "deleted_faces": len(pinecone_ids)
    }
