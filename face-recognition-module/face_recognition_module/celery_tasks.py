"""
Celery tasks for face recognition module.

This module provides background task support for:
- Scanning known_faces folder and indexing people
- Batch reprocessing gallery photos to tag known people
- Orchestrating scan and reprocess operations together
"""

import logging
from typing import Dict, Any, List
from datetime import datetime
from bson import ObjectId

from face_recognition_module import FaceScanner
from face_recognition_module.database import KnownPeopleDB

logger = logging.getLogger(__name__)


def get_celery_app():
    """Get Celery app instance from backend."""
    try:
        from backend.workers.celery_app import celery_app
        return celery_app
    except ImportError:
        logger.error("Could not import celery_app from backend")
        return None


def get_database():
    """Get MongoDB database instance from backend."""
    try:
        from backend.config.database import get_database
        return get_database()
    except ImportError:
        logger.error("Could not import get_database from backend")
        return None


def get_face_service():
    """Get FaceService instance from backend."""
    try:
        from backend.services.face_service import FaceService
        return FaceService()
    except ImportError:
        logger.error("Could not import FaceService from backend")
        return None


# Register tasks with Celery app
celery_app = get_celery_app()


@celery_app.task(name='face_recognition_module.scan_known_faces_task')
def scan_known_faces_task(update_existing: bool = False) -> Dict[str, Any]:
    """
    Background task to scan known_faces folder and index known people.

    Args:
        update_existing: If True, update existing people with new photos

    Returns:
        Dictionary with scan results:
        {
            "success": bool,
            "total_people": int,
            "processed_people": int,
            "failed_people": int,
            "errors": List[str]
        }
    """
    logger.info(f"[CELERY] Starting scan_known_faces_task (update_existing={update_existing})")

    try:
        db = KnownPeopleDB()
        db.connect()

        scanner = FaceScanner(db=db)
        results = scanner.scan_known_faces(update_existing=update_existing)

        logger.info(f"[CELERY] Scan complete: {results['processed_people']}/{results['total_people']} people processed")

        return results

    except Exception as e:
        logger.error(f"[CELERY] Error in scan_known_faces_task: {e}")
        return {
            "success": False,
            "total_people": 0,
            "processed_people": 0,
            "failed_people": 0,
            "errors": [str(e)]
        }
    finally:
        if 'db' in locals():
            db.disconnect()


@celery_app.task(name='face_recognition_module.reprocess_photo_for_tagging')
def reprocess_photo_for_tagging(photo_id: str) -> Dict[str, Any]:
    """
    Background task to reprocess single photo and tag known people.

    This task expects photo to already have detected_faces array populated.
    It only handles face matching, not face detection.

    Args:
        photo_id: MongoDB ObjectId of photo to reprocess

    Returns:
        Dictionary with reprocessing results:
        {
            "photo_id": str,
            "tagged_count": int,
            "status": "success" or "skipped" or "failed",
            "error": str (if failed)
        }
    """
    logger.info(f"[CELERY] Reprocessing photo {photo_id} for tagging")

    try:
        db = get_database()
        if not db:
            return {"photo_id": photo_id, "status": "failed", "error": "Could not get database connection"}

        from backend.models.database import PHOTOS, KNOWN_PEOPLE, to_object_id

        # Convert to ObjectId
        photo_obj_id = to_object_id(photo_id)

        # Get photo from database
        photo = db[PHOTOS].find_one({"_id": photo_obj_id})
        if not photo:
            logger.warning(f"[CELERY] Photo {photo_id} not found")
            return {"photo_id": photo_id, "status": "skipped", "error": "Photo not found"}

        # Check if photo has detected faces
        if not photo.get("detected_faces") or len(photo.get("detected_faces", [])) == 0:
            logger.info(f"[CELERY] Photo {photo_id} has no detected faces, skipping")
            return {"photo_id": photo_id, "status": "skipped", "error": "No detected faces"}

        # Check if known_people database has data
        known_people_count = db[KNOWN_PEOPLE].count_documents({})
        if known_people_count == 0:
            logger.info(f"[CELERY] No known people in database for photo {photo_id}")
            return {"photo_id": photo_id, "tagged_count": 0, "status": "success"}

        # Get faces from embedded array
        faces = photo.get("faces", [])
        if not faces:
            logger.warning(f"[CELERY] No faces found in photo {photo_id}")
            return {"photo_id": photo_id, "status": "skipped", "error": "No faces in photo"}

        # Match faces against known_people
        tagged_people = []
        face_service = get_face_service()

        if not face_service:
            logger.warning(f"[CELERY] Could not initialize FaceService for photo {photo_id}")
            return {"photo_id": photo_id, "status": "failed", "error": "FaceService not available"}

        try:
            for face in faces:
                face_id = face["_id"]
                embedding = face.get("embedding")

                if not embedding:
                    logger.warning(f"[CELERY] Face {face_id} has no embedding, skipping")
                    continue

                # Extract bbox
                bbox_x1 = face.get("bbox_x1", 0)
                bbox_y1 = face.get("bbox_y1", 0)
                bbox_x2 = face.get("bbox_x2", 100)
                bbox_y2 = face.get("bbox_y2", 100)
                bbox = (int(bbox_x1), int(bbox_y1), int(bbox_x2), int(bbox_y2))

                # Query known_people for matches
                try:
                    matches = face_service._db.query_known_people(
                        embedding,
                        top_k=1,
                        score_threshold=0.7
                    )

                    for match in matches:
                        # Fetch full person data
                        person_id = ObjectId(match['id'])
                        person = db[KNOWN_PEOPLE].find_one({"_id": person_id})

                        if person:
                            # Convert Pinecone score [-1, 1] to confidence [0, 1]
                            confidence = (match['score'] + 1) / 2

                            tagged_entry = create_tagged_person_entry(
                                person_id=person_id,
                                name=person['name'],
                                confidence=confidence,
                                bbox_x1=bbox[0],
                                bbox_y1=bbox[1],
                                bbox_x2=bbox[2],
                                bbox_y2=bbox[3],
                                face_id=face_id,
                                role=person.get('role')
                            )
                            tagged_people.append(tagged_entry)
                            logger.info(f"[CELERY] Photo {photo_id}: Matched face to {person['name']} (confidence: {confidence:.2f})")

                except AttributeError:
                    logger.warning(f"[CELERY] Photo {photo_id}: Pinecone not available, skipping face matching")
                    break
                except Exception as e:
                    logger.warning(f"[CELERY] Photo {photo_id}: Error matching face: {e}")
                    continue

            # Update photo with tagged_people
            update_doc = {
                "reprocessed_at": datetime.utcnow()
            }

            if tagged_people:
                update_doc["tagged_people"] = tagged_people
                logger.info(f"[CELERY] Photo {photo_id}: Tagged {len(tagged_people)} people")

            db[PHOTOS].update_one(
                {"_id": photo_obj_id},
                {"$set": update_doc}
            )

            return {
                "photo_id": photo_id,
                "tagged_count": len(tagged_people),
                "status": "success"
            }

        except Exception as e:
            logger.error(f"[CELERY] Error tagging photo {photo_id}: {e}")
            return {
                "photo_id": photo_id,
                "status": "failed",
                "error": str(e)
            }

    except Exception as e:
        logger.error(f"[CELERY] Unexpected error in reprocess_photo_for_tagging: {e}")
        return {
            "photo_id": photo_id,
            "status": "failed",
            "error": str(e)
        }


@celery_app.task(name='face_recognition_module.reprocess_all_photos_task')
def reprocess_all_photos_task() -> Dict[str, Any]:
    """
    Background task to batch reprocess all existing photos and tag known people.

    This task queries all photos in the database and reprocesses them to tag
    any known people identified in the photos.

    Returns:
        Dictionary with batch results:
        {
            "status": "completed" or "failed",
            "total_photos": int,
            "processed": int,
            "tagged": int,
            "skipped": int,
            "failed": int,
            "errors": List[str]
        }
    """
    logger.info("[CELERY] Starting reprocess_all_photos_task")

    try:
        db = get_database()
        if not db:
            return {
                "status": "failed",
                "total_photos": 0,
                "processed": 0,
                "tagged": 0,
                "skipped": 0,
                "failed": 0,
                "errors": ["Could not get database connection"]
            }

        from backend.models.database import PHOTOS

        # Get all completed photos
        all_photos = list(db[PHOTOS].find({"processing_status": "completed"}))
        total_photos = len(all_photos)

        logger.info(f"[CELERY] Found {total_photos} completed photos to reprocess")

        stats = {
            "status": "completed",
            "total_photos": total_photos,
            "processed": 0,
            "tagged": 0,
            "skipped": 0,
            "failed": 0,
            "errors": []
        }

        if total_photos == 0:
            logger.info("[CELERY] No photos to reprocess")
            return stats

        # Process each photo
        for idx, photo in enumerate(all_photos, 1):
            photo_id = str(photo["_id"])

            # Log progress every 10 photos
            if idx % 10 == 0:
                logger.info(f"[CELERY] Reprocessing progress: {idx}/{total_photos}")

            try:
                # Call reprocess task for this photo
                result = reprocess_photo_for_tagging(photo_id)

                if result["status"] == "success":
                    stats["processed"] += 1
                    if result.get("tagged_count", 0) > 0:
                        stats["tagged"] += 1
                elif result["status"] == "skipped":
                    stats["skipped"] += 1
                else:  # failed
                    stats["failed"] += 1
                    stats["errors"].append(f"Photo {photo_id}: {result.get('error', 'Unknown error')}")

            except Exception as e:
                logger.error(f"[CELERY] Error reprocessing photo {photo_id}: {e}")
                stats["failed"] += 1
                stats["errors"].append(f"Photo {photo_id}: {str(e)}")

        logger.info(f"[CELERY] Reprocess all photos completed: processed={stats['processed']}, tagged={stats['tagged']}, skipped={stats['skipped']}, failed={stats['failed']}")

        return stats

    except Exception as e:
        logger.error(f"[CELERY] Unexpected error in reprocess_all_photos_task: {e}")
        return {
            "status": "failed",
            "total_photos": 0,
            "processed": 0,
            "tagged": 0,
            "skipped": 0,
            "failed": 0,
            "errors": [str(e)]
        }


@celery_app.task(name='face_recognition_module.scan_and_reprocess_all_task')
def scan_and_reprocess_all_task(update_existing: bool = False) -> Dict[str, Any]:
    """
    Orchestrator task that scans known_faces and then reprocesses all photos.

    This task:
    1. Scans known_faces folder and indexes known people
    2. If scan succeeds, automatically starts batch reprocessing of all photos

    Args:
        update_existing: If True, update existing people during scan

    Returns:
        Dictionary with combined results:
        {
            "status": "completed" or "failed",
            "scan_results": {
                "success": bool,
                "total_people": int,
                ...
            },
            "reprocess_results": {
                "status": str,
                "total_photos": int,
                ...
            } or None if scan failed
        }
    """
    logger.info("[CELERY] Starting scan_and_reprocess_all_task (orchestrator)")

    try:
        # Step 1: Scan known_faces
        logger.info("[CELERY] Step 1: Scanning known_faces folder...")
        scan_results = scan_known_faces_task(update_existing=update_existing)

        if not scan_results.get("success"):
            logger.error("[CELERY] Scan failed, aborting reprocessing")
            return {
                "status": "failed",
                "scan_results": scan_results,
                "reprocess_results": None,
                "error": "Scan failed"
            }

        logger.info(f"[CELERY] Scan successful: {scan_results['processed_people']} people indexed")

        # Step 2: Reprocess all photos
        logger.info("[CELERY] Step 2: Reprocessing all photos...")
        reprocess_results = reprocess_all_photos_task()

        logger.info("[CELERY] Orchestrator task completed")

        return {
            "status": "completed",
            "scan_results": scan_results,
            "reprocess_results": reprocess_results
        }

    except Exception as e:
        logger.error(f"[CELERY] Error in orchestrator task: {e}")
        return {
            "status": "failed",
            "scan_results": None,
            "reprocess_results": None,
            "error": str(e)
        }


# Task routing (for Celery configuration)
TASK_ROUTES = {
    'face_recognition_module.scan_known_faces_task': {'queue': 'face_recognition'},
    'face_recognition_module.reprocess_photo_for_tagging': {'queue': 'face_recognition'},
    'face_recognition_module.reprocess_all_photos_task': {'queue': 'batch_processing'},
    'face_recognition_module.scan_and_reprocess_all_task': {'queue': 'batch_processing'},
}
