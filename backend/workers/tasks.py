"""
Celery tasks for face recognition processing - MongoDB version
"""

from celery import Task, group
from pymongo.database import Database
import numpy as np
from io import BytesIO
from PIL import Image
import logging
import uuid
from datetime import datetime
from bson import ObjectId

from backend.workers.celery_app import celery_app
from backend.config.database import get_database
from backend.models.database import (
    PHOTOS, GALLERIES, USERS,
    to_object_id, from_object_id
)
from backend.services.face_service import FaceService
from backend.services.storage_service import StorageService

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Base task with database connection"""
    _db = None
    _face_service = None
    _storage_service = None

    @property
    def db(self) -> Database:
        if self._db is None:
            self._db = get_database()
        return self._db

    @property
    def face_service(self) -> FaceService:
        if self._face_service is None:
            self._face_service = FaceService()
        return self._face_service

    @property
    def storage_service(self) -> StorageService:
        if self._storage_service is None:
            self._storage_service = StorageService()
        return self._storage_service

    def after_return(self, *args, **kwargs):
        # MongoDB connections are managed globally, no cleanup needed
        pass


@celery_app.task(
    base=DatabaseTask,
    bind=True,
    name='tasks.process_photo',
    queue='photo_processing',
    max_retries=3,
    default_retry_delay=60
)
def process_photo(self, photo_id: str, gallery_id: str):
    """Process uploaded photo: detect faces, extract embeddings, match with users"""
    logger.info(f"🚀 Photo {photo_id}")

    try:
        db = self.db

        # Convert string IDs to ObjectId
        photo_obj_id = to_object_id(photo_id)
        gallery_obj_id = to_object_id(gallery_id)

        photo = db[PHOTOS].find_one({"_id": photo_obj_id})
        if not photo:
            return {"error": "Photo not found"}

        # Update processing status
        db[PHOTOS].update_one(
            {"_id": photo_obj_id},
            {"$set": {"processing_status": "processing"}}
        )

        # Download from storage
        image_data = self.storage_service.download_file(photo["file_path"])
        if not image_data:
            db[PHOTOS].update_one(
                {"_id": photo_obj_id},
                {"$set": {"processing_status": "failed"}}
            )
            return {"error": "Storage download failed"}

        # Convert to array
        image = Image.open(BytesIO(image_data))
        image_array = np.array(image)

        # Detect faces
        faces_data = self.face_service.detect_faces(image_array)

        if not faces_data:
            db[PHOTOS].update_one(
                {"_id": photo_obj_id},
                {
                    "$set": {
                        "processing_status": "completed",
                        "face_count": 0,
                        "processed_at": datetime.utcnow()
                    }
                }
            )
            logger.info(f"Photo {photo_id}: No faces detected")
            return {"photo_id": photo_id, "faces_detected": 0}

        logger.info(f"Photo {photo_id}: Detected {len(faces_data)} faces")

        # Batch prepare all face data
        face_records = []
        embeddings_batch = []

        for idx, face_data in enumerate(faces_data, 1):
            confidence = face_data.get('det_score') or face_data.get('confidence') or 0.9
            bbox = face_data.get('bbox', [0, 0, 100, 100])

            if isinstance(bbox, dict):
                x1, y1, x2, y2 = int(bbox['x1']), int(bbox['y1']), int(bbox['x2']), int(bbox['y2'])
            else:
                x1, y1, x2, y2 = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])

            pinecone_id = f"face_{photo_id}_{uuid.uuid4().hex[:8]}"

            face_records.append({
                'pinecone_id': pinecone_id,
                'bbox': (x1, y1, x2, y2),
                'embedding': face_data['embedding'].tolist(),  # Convert numpy array to list for MongoDB
                'confidence': confidence
            })

            # Store raw embedding from InsightFace (already normalized)
            raw_embedding = face_data['embedding']

            embeddings_batch.append({
                "id": pinecone_id,
                "embedding": raw_embedding,
                "metadata": {
                    "type": "gallery_face",
                    "photo_id": photo_id,
                    "gallery_id": gallery_id,
                    "bbox_x1": x1,
                    "bbox_y1": y1,
                    "bbox_x2": x2,
                    "bbox_y2": y2,
                    "confidence": float(confidence)
                }
            })

        # Single batch upload to Pinecone
        self.face_service._db.upsert_embeddings(embeddings_batch)

        # Build embedded faces array (NO EMBEDDINGS - stored only in Pinecone)
        faces_array = []
        for face_rec in face_records:
            face_doc = {
                "bbox_x1": face_rec['bbox'][0],
                "bbox_y1": face_rec['bbox'][1],
                "bbox_x2": face_rec['bbox'][2],
                "bbox_y2": face_rec['bbox'][3],
                "pinecone_id": face_rec['pinecone_id'],
                "confidence": face_rec['confidence']
                # NO embedding field - stored only in Pinecone
            }
            faces_array.append(face_doc)

        # Update photo with embedded faces array and final status
        db[PHOTOS].update_one(
            {"_id": photo_obj_id},
            {
                "$set": {
                    "faces": faces_array,
                    "processing_status": "completed",
                    "face_count": len(faces_data),
                    "processed_at": datetime.utcnow()
                }
            }
        )

        logger.info(f"🎉 Photo {photo_id}: {len(faces_data)} faces embedded and stored")

        return {
            "photo_id": photo_id,
            "faces_detected": len(faces_data),
            "status": "completed"
        }

    except Exception as e:
        logger.error(f"❌ Photo {photo_id}: {str(e)}")
        try:
            photo_obj_id = to_object_id(photo_id)
            db[PHOTOS].update_one(
                {"_id": photo_obj_id},
                {"$set": {"processing_status": "failed"}}
            )
        except:
            pass
        raise self.retry(exc=e)


@celery_app.task(
    base=DatabaseTask,
    bind=True,
    name='tasks.create_user_profile',
    queue='profile_creation',
    max_retries=3,
    default_retry_delay=60
)
def create_user_profile(self, user_id: str):
    """Create user face profile from reference photos"""
    logger.info(f"🚀 Profile {user_id}")

    try:
        db = self.db

        # Convert string ID to ObjectId
        user_obj_id = to_object_id(user_id)

        user = db[USERS].find_one({"_id": user_obj_id})

        if not user:
            return {"error": "User not found"}

        # Update processing status
        db[USERS].update_one(
            {"_id": user_obj_id},
            {"$set": {"processing_status": "processing"}}
        )

        # Access embedded reference_photos array
        reference_photos = user.get("reference_photos", [])

        if not reference_photos:
            db[USERS].update_one(
                {"_id": user_obj_id},
                {"$set": {"processing_status": "failed"}}
            )
            return {"error": "No reference photos"}

        all_embeddings = []
        processed_photos = 0

        for ref_photo in reference_photos:
            image_data = self.storage_service.download_file(ref_photo["file_path"])
            if not image_data:
                continue

            image = Image.open(BytesIO(image_data))
            image_array = np.array(image)

            faces_data = self.face_service.detect_faces(image_array)
            if not faces_data:
                continue

            best_face = max(faces_data, key=lambda x: x.get('det_score', x.get('confidence', 0)))
            all_embeddings.append(best_face['embedding'])
            processed_photos += 1

            # Mark reference photo as processed (using positional operator)
            db[USERS].update_one(
                {"_id": user_obj_id, "reference_photos._id": ref_photo["_id"]},
                {"$set": {"reference_photos.$.processed": True}}
            )

        if not all_embeddings:
            db[USERS].update_one(
                {"_id": user_obj_id},
                {"$set": {"processing_status": "failed"}}
            )
            return {"error": "No faces detected"}

        # Average embedding (InsightFace already provides normalized embeddings)
        # We just average them - no additional normalization needed
        avg_embedding = np.mean(all_embeddings, axis=0)

        # Log embedding stats for debugging
        embedding_norm = np.linalg.norm(avg_embedding)
        logger.info(f"User {user_id} embedding stats: shape={avg_embedding.shape}, norm={embedding_norm:.4f}, min={avg_embedding.min():.4f}, max={avg_embedding.max():.4f}")

        # Store in Pinecone (raw averaged embedding without normalization)
        logger.info(f"User {user_id}: Uploading profile embedding to Pinecone with ID 'user:{user_id}'")
        self.face_service._db.upsert_embeddings([{
            "id": f"user:{user_id}",
            "embedding": avg_embedding,
            "metadata": {
                "type": "user_profile",
                "user_id": user_id,
                "reference_photos_count": processed_photos
            }
        }])
        logger.info(f"User {user_id}: Profile embedding successfully uploaded to Pinecone")

        # Update user document with profile data
        db[USERS].update_one(
            {"_id": user_obj_id},
            {
                "$set": {
                    "processing_status": "completed",
                    "avg_embedding": str(avg_embedding.tolist()),
                    "reference_photo_count": processed_photos,
                    "profile_updated_at": datetime.utcnow()
                }
            }
        )

        logger.info(f"✅ Profile {user_id}")

        # Note: Retroactive scan is now triggered via Celery chain from API endpoint
        # This prevents race condition where scan starts before profile is fully saved

        return {
            "user_id": user_id,
            "embeddings_processed": processed_photos,
            "status": "completed"
        }

    except Exception as e:
        logger.error(f"❌ Profile {user_id}: {str(e)}")
        try:
            user_obj_id = to_object_id(user_id)
            db[USERS].update_one(
                {"_id": user_obj_id},
                {"$set": {"processing_status": "failed"}}
            )
        except:
            pass
        raise self.retry(exc=e)


@celery_app.task(
    base=DatabaseTask,
    bind=True,
    name='tasks.scan_all_galleries_for_user',
    queue='photo_processing'
)
def scan_all_galleries_for_user(self, user_id: str):
    """
    Retroactively scan all existing gallery photos for a user.
    Uses optimized Pinecone vector search to find matches in one query.
    """
    logger.info(f"🔍 Scan galleries for user {user_id}")

    try:
        db = self.db

        # Convert string ID to ObjectId
        user_obj_id = to_object_id(user_id)

        # Get user with embedded profile
        user = db[USERS].find_one({"_id": user_obj_id})

        if not user or not user.get("avg_embedding"):
            logger.warning(f"User {user_id}: No profile or embedding found")
            return {"error": "No profile"}

        import json
        user_embedding = np.array(json.loads(user["avg_embedding"]))

        logger.info(f"🔍 Searching Pinecone for faces matching user {user_id} (threshold >= 0.7)")

        # Use Pinecone's optimized vector search - single query for ALL gallery faces
        # This is much faster than fetching and comparing each face individually
        matches = self.face_service.search_similar_faces(
            user_embedding,
            top_k=10000,          # Get up to 10,000 best matches
            score_threshold=0.7   # Only return matches >= 0.7 confidence
        )

        # Filter to only gallery faces (not other user profiles)
        gallery_matches = [
            m for m in matches
            if m.get('type') == 'gallery_face' and m.get('photo_id')
        ]

        logger.info(f"📊 Found {len(gallery_matches)} gallery face matches above threshold 0.7")

        # Create matched_users associations in photos (embedded array)
        associations_created = 0

        for match in gallery_matches:
            # Find photo by embedded faces.pinecone_id
            photo = db[PHOTOS].find_one({"faces.pinecone_id": match['pinecone_id']})
            if not photo:
                logger.warning(f"Photo not found for pinecone_id: {match['pinecone_id']}")
                continue

            # Find face_index in the embedded faces array
            faces = photo.get("faces", [])
            face_index = next(
                (i for i, f in enumerate(faces) if f["pinecone_id"] == match['pinecone_id']),
                None
            )

            if face_index is None:
                continue

            # Check if association already exists in matched_users array
            matched_users = photo.get("matched_users", [])
            existing = next(
                (m for m in matched_users
                 if m["user_id"] == user_obj_id and m["face_index"] == face_index),
                None
            )

            if existing:
                continue

            # Add to matched_users array
            matched_user_doc = {
                "user_id": user_obj_id,
                "face_index": face_index,
                "confidence": match['confidence'],
                "created_at": datetime.utcnow()
            }

            db[PHOTOS].update_one(
                {"_id": photo["_id"]},
                {"$push": {"matched_users": matched_user_doc}}
            )
            associations_created += 1
        logger.info(f"✅ User {user_id}: Created {associations_created} new associations")

        return {
            "user_id": user_id,
            "associations_created": associations_created,
            "total_matches_found": len(gallery_matches)
        }

    except Exception as e:
        logger.error(f"❌ Scan user {user_id}: {str(e)}")
        raise


@celery_app.task(
    base=DatabaseTask,
    bind=True,
    name='tasks.tag_known_people_in_photo',
    queue='photo_processing',
    max_retries=2,
    default_retry_delay=60
)
def tag_known_people_in_photo(self, photo_id: str):
    """Match a single photo against all known people from known_faces directory."""
    logger.info(f"🏷️  Tagging known people in photo {photo_id}")

    try:
        db = self.db

        # Convert string ID to ObjectId
        photo_obj_id = to_object_id(photo_id)

        photo = db[PHOTOS].find_one({"_id": photo_obj_id})
        if not photo:
            return {"error": "Photo not found"}

        # Get embedded faces array from photo
        faces = photo.get("faces", [])
        if not faces:
            logger.info(f"Photo {photo_id}: No faces to match")
            return {"photo_id": photo_id, "matches_found": 0}

        # Fetch embeddings from Pinecone (not stored in MongoDB anymore)
        pinecone_ids = [face['pinecone_id'] for face in faces]
        pinecone_index = self.face_service._db.index

        # Fetch vectors from Pinecone
        fetch_response = pinecone_index.fetch(ids=pinecone_ids)

        # Prepare detected faces with embeddings from Pinecone
        detected_faces = []
        for idx, face in enumerate(faces):
            pinecone_id = face['pinecone_id']
            if pinecone_id in fetch_response.get('vectors', {}):
                embedding_data = fetch_response['vectors'][pinecone_id]
                embedding = np.array(embedding_data['values'])

                detected_faces.append({
                    'embedding': embedding,
                    'face_index': idx,
                    'bbox': (face.get('bbox_x1', 0), face.get('bbox_y1', 0),
                            face.get('bbox_x2', 0), face.get('bbox_y2', 0))
                })

        if not detected_faces:
            logger.info(f"Photo {photo_id}: No embeddings available from Pinecone")
            return {"photo_id": photo_id, "matches_found": 0}

        # Initialize FaceMatcher for known people
        from face_recognition_module import FaceMatcher
        from face_recognition_module.database import KnownPeopleDB

        known_people_db = KnownPeopleDB()
        known_people_db.connect()

        try:
            matcher = FaceMatcher(db=known_people_db)

            # Match all faces in this photo against known people
            all_matches = matcher.match_multiple_embeddings(
                [f['embedding'] for f in detected_faces],
                use_pinecone=True
            )

            total_matches = 0

            # For each face's matches, add to tagged_people array (embedded in photo)
            for face_idx, face_matches in enumerate(all_matches):
                face_index_in_photo = detected_faces[face_idx]['face_index']

                for match in face_matches:
                    # Check if this match already exists in tagged_people array
                    tagged_people = photo.get('tagged_people', [])
                    existing = next(
                        (t for t in tagged_people
                         if t.get('person_id') == to_object_id(match['person_id']) and t.get('face_index') == face_index_in_photo),
                        None
                    )

                    if not existing:
                        tagged_person_doc = {
                            'person_id': to_object_id(match['person_id']),
                            'person_name': match['name'],
                            'face_index': face_index_in_photo,
                            'confidence': match['confidence'],
                            'linkedin_profile': match.get('linkedin_profile'),
                            'created_at': datetime.utcnow()
                        }

                        db[PHOTOS].update_one(
                            {"_id": photo_obj_id},
                            {"$push": {"tagged_people": tagged_person_doc}}
                        )
                        total_matches += 1

                        # Reload photo for next iteration
                        photo = db[PHOTOS].find_one({"_id": photo_obj_id})

            logger.info(f"✅ Photo {photo_id}: Tagged {total_matches} known people")
            return {
                "photo_id": photo_id,
                "matches_found": total_matches,
                "status": "completed"
            }

        finally:
            known_people_db.disconnect()

    except Exception as e:
        logger.error(f"❌ Tag photo {photo_id}: {str(e)}")
        raise self.retry(exc=e)


@celery_app.task(
    base=DatabaseTask,
    bind=True,
    name='tasks.tag_known_people_in_gallery',
    queue='photo_processing',
    max_retries=2,
    default_retry_delay=60
)
def tag_known_people_in_gallery(self, gallery_id: str):
    """
    REVERSE MATCHING: Tag known people in a gallery by querying Pinecone
    with each known person's embedding to find similar gallery faces.

    This is much faster than iterating through all photos because:
    - N queries (one per known person) vs N*M comparisons
    - Pinecone handles the similarity search efficiently
    """
    logger.info(f"[TAG] Tagging known people in gallery {gallery_id} (reverse matching)")

    try:
        db = self.db

        # Convert string ID to ObjectId
        gallery_obj_id = to_object_id(gallery_id)

        gallery = db[GALLERIES].find_one({"_id": gallery_obj_id})
        if not gallery:
            return {"error": "Gallery not found"}

        # Initialize FaceMatcher with Pinecone for reverse matching
        from face_recognition_module import FaceMatcher
        from face_recognition_module.database import KnownPeopleDB
        from backend.core.database.pinecone_db import PineconeDatabase
        from backend.config.settings import get_settings

        settings = get_settings()

        # Initialize Pinecone - required for reverse matching
        try:
            pinecone_db = PineconeDatabase(
                api_key=settings.PINECONE_API_KEY,
                index_name=settings.PINECONE_INDEX_NAME,
                environment=settings.PINECONE_ENVIRONMENT
            )
        except Exception as e:
            logger.error(f"[ERROR] Pinecone required for reverse matching: {e}")
            raise self.retry(exc=e)

        known_people_db = KnownPeopleDB()
        known_people_db.connect()

        try:
            # Initialize matcher with both databases
            matcher = FaceMatcher(
                db=known_people_db,
                pinecone_db=pinecone_db,
                confidence_threshold=0.7
            )

            # Get all known people
            known_people = matcher.get_all_known_people()
            logger.info(f"[INFO] Processing {len(known_people)} known people...")

            total_matches = 0
            new_matches = 0
            people_with_matches = 0

            # Get photo IDs in this gallery for filtering matches
            gallery_photo_ids = set(
                str(p['_id']) for p in db[PHOTOS].find(
                    {"gallery_id": gallery_obj_id, "face_count": {"$gt": 0}},
                    {"_id": 1}
                )
            )

            if not gallery_photo_ids:
                logger.info(f"Gallery {gallery_id}: No photos with faces")
                return {"gallery_id": gallery_id, "photos_processed": 0, "matches_found": 0}

            # For each known person, query Pinecone for similar gallery faces
            for person in known_people:
                person_name = person.get("name", "Unknown")
                person_id = person.get("person_id")
                linkedin_profile = person.get("linkedin_profile")
                avg_embedding = person.get("average_embedding")

                if not avg_embedding:
                    continue

                # Query Pinecone with this person's embedding
                matches = matcher.find_gallery_faces_for_known_person(
                    person_embedding=avg_embedding,
                    top_k=1000,
                    threshold=0.7
                )

                person_matches = 0

                for match in matches:
                    photo_id = match.get("photo_id")
                    if not photo_id:
                        continue

                    # Filter to only this gallery's photos
                    if photo_id not in gallery_photo_ids:
                        continue

                    try:
                        photo_obj_id = to_object_id(photo_id)
                    except:
                        continue

                    # Get photo to access embedded arrays
                    photo = db[PHOTOS].find_one({"_id": photo_obj_id})
                    if not photo:
                        continue

                    # Find face_index from pinecone_id in embedded faces array
                    faces = photo.get("faces", [])
                    face_index = next(
                        (i for i, f in enumerate(faces) if f.get('pinecone_id') == match.get('pinecone_id')),
                        None
                    )

                    if face_index is None:
                        continue

                    # Check for existing match in tagged_people array
                    tagged_people = photo.get("tagged_people", [])
                    existing_idx = next(
                        (i for i, t in enumerate(tagged_people)
                         if t.get('person_id') == to_object_id(person_id) and t.get('face_index') == face_index),
                        None
                    )

                    if existing_idx is None:
                        # Add new tagged person
                        db[PHOTOS].update_one(
                            {"_id": photo_obj_id},
                            {"$push": {"tagged_people": {
                                'person_id': to_object_id(person_id),
                                'person_name': person_name,
                                'face_index': face_index,
                                'confidence': match['confidence'],
                                'linkedin_profile': linkedin_profile,
                                'created_at': datetime.utcnow()
                            }}}
                        )
                        new_matches += 1
                    else:
                        # Update if higher confidence
                        existing = tagged_people[existing_idx]
                        if match['confidence'] > existing.get('confidence', 0):
                            db[PHOTOS].update_one(
                                {"_id": photo_obj_id},
                                {"$set": {
                                    f"tagged_people.{existing_idx}.confidence": match['confidence'],
                                    f"tagged_people.{existing_idx}.updated_at": datetime.utcnow()
                                }}
                            )

                    person_matches += 1
                    total_matches += 1

                if person_matches > 0:
                    people_with_matches += 1
                    logger.info(f"  {person_name}: {person_matches} matches in this gallery")

            logger.info(f"[OK] Gallery {gallery_id}: {total_matches} matches ({new_matches} new) for {people_with_matches} people")

            # Chain LinkedIn sync task to update matches with LinkedIn profiles
            logger.info(f"[CHAIN] Triggering LinkedIn sync for gallery {gallery_id}")
            celery_app.send_task(
                'tasks.sync_linkedin_to_gallery_matches',
                args=[gallery_id]
            )

            return {
                "gallery_id": gallery_id,
                "known_people_processed": len(known_people),
                "people_with_matches": people_with_matches,
                "total_matches_found": total_matches,
                "new_matches_inserted": new_matches,
                "status": "completed"
            }

        finally:
            known_people_db.disconnect()

    except Exception as e:
        logger.error(f"[ERROR] Tag gallery {gallery_id}: {str(e)}")
        raise self.retry(exc=e)


@celery_app.task(
    base=DatabaseTask,
    bind=True,
    name='tasks.sync_linkedin_to_gallery_matches',
    queue='photo_processing',
    max_retries=2,
    default_retry_delay=30
)
def sync_linkedin_to_gallery_matches(self, gallery_id: str):
    """
    Sync LinkedIn profiles from known_people to known_faces_matches for a specific gallery.
    This ensures all matches have the latest LinkedIn URLs.
    """
    logger.info(f"[LINKEDIN] Syncing LinkedIn profiles for gallery {gallery_id}")

    try:
        db = self.db
        gallery_obj_id = to_object_id(gallery_id)

        # Get all photos in this gallery
        photos = list(db[PHOTOS].find({"gallery_id": gallery_obj_id}))

        if not photos:
            logger.info(f"Gallery {gallery_id}: No photos found")
            return {"gallery_id": gallery_id, "updated": 0}

        # Get all known people with LinkedIn profiles
        known_people_map = {
            str(p['_id']): p.get('linkedin_profile')
            for p in db['known_people'].find({}, {"_id": 1, "linkedin_profile": 1})
        }

        # Update tagged_people array in photos with LinkedIn profiles
        updated_count = 0
        total_matches = 0

        for photo in photos:
            tagged_people = photo.get("tagged_people", [])
            if not tagged_people:
                continue

            total_matches += len(tagged_people)

            for idx, tagged in enumerate(tagged_people):
                person_id = str(tagged.get('person_id'))
                if person_id in known_people_map:
                    new_linkedin = known_people_map[person_id]
                    old_linkedin = tagged.get('linkedin_profile')

                    if new_linkedin and new_linkedin != old_linkedin:
                        db[PHOTOS].update_one(
                            {"_id": photo["_id"]},
                            {"$set": {f"tagged_people.{idx}.linkedin_profile": new_linkedin}}
                        )
                        updated_count += 1

        logger.info(f"[INFO] Found {total_matches} tagged people to sync")

        logger.info(f"[OK] Gallery {gallery_id}: Updated {updated_count} matches with LinkedIn profiles")
        return {
            "gallery_id": gallery_id,
            "total_matches": len(matches),
            "updated": updated_count,
            "status": "completed"
        }

    except Exception as e:
        logger.error(f"[ERROR] LinkedIn sync for gallery {gallery_id}: {str(e)}")
        raise self.retry(exc=e)


__all__ = ['process_photo', 'create_user_profile', 'scan_all_galleries_for_user', 'tag_known_people_in_photo', 'tag_known_people_in_gallery', 'sync_linkedin_to_gallery_matches']
