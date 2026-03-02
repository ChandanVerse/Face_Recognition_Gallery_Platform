"""
Face matcher for comparing detected faces against known people database.
"""
import logging
from typing import Optional, List, Dict, Any, Tuple
import numpy as np
from . import config
from .database import KnownPeopleDB

logger = logging.getLogger(__name__)


class FaceMatcher:
    """Match detected faces against known people database."""

    def __init__(
        self,
        db: Optional[KnownPeopleDB] = None,
        pinecone_db=None,
        confidence_threshold: Optional[float] = None
    ):
        """Initialize face matcher.

        Args:
            db: KnownPeopleDB instance
            pinecone_db: Pinecone database instance
            confidence_threshold: Confidence threshold for matches (0.0-1.0)
        """
        self.db = db
        self.pinecone_db = pinecone_db
        self.confidence_threshold = confidence_threshold or config.CONFIDENCE_THRESHOLD

    def match_face_embedding(
        self,
        embedding: List[float],
        top_k: int = 1,
        use_pinecone: bool = True
    ) -> List[Dict[str, Any]]:
        """Match a face embedding against known people.

        Args:
            embedding: Face embedding (list of 512 floats)
            top_k: Number of top matches to return
            use_pinecone: If True, use Pinecone for search (faster for large datasets)

        Returns:
            List of matches, each containing:
            {
                "person_id": str,
                "name": str,
                "confidence": float,
                "linkedin_profile": str (optional)
            }
        """
        if use_pinecone and self.pinecone_db:
            return self._match_with_pinecone(embedding, top_k)
        else:
            return self._match_with_mongodb(embedding, top_k)

    def _match_with_pinecone(
        self,
        embedding: List[float],
        top_k: int = 1
    ) -> List[Dict[str, Any]]:
        """Match using Pinecone vector similarity search.

        Args:
            embedding: Face embedding
            top_k: Number of top matches

        Returns:
            List of matches above confidence threshold
        """
        try:
            # Query Pinecone
            results = self.pinecone_db.query(
                vector=embedding,
                top_k=top_k,
                namespace=config.PINECONE_NAMESPACE_KNOWN
            )

            matches = []
            for match in results:
                # Pinecone returns scores in range [-1, 1], convert to [0, 1]
                confidence = (match['score'] + 1) / 2

                if confidence >= self.confidence_threshold:
                    person_id = match['id']

                    # Fetch person details from MongoDB
                    person_data = None
                    if self.db:
                        from bson import ObjectId
                        try:
                            person_data = self.db.get_known_person_by_id(ObjectId(person_id))
                        except Exception as e:
                            logger.warning(f"Could not fetch person {person_id} from DB: {e}")

                    match_info = {
                        "person_id": person_id,
                        "name": match['metadata'].get('person_name', 'Unknown'),
                        "confidence": confidence,
                    }

                    if person_data:
                        match_info["linkedin_profile"] = person_data.get("linkedin_profile")
                        match_info["metadata"] = person_data.get("metadata", {})

                    matches.append(match_info)

            logger.info(f"Found {len(matches)} matches above confidence {self.confidence_threshold}")
            return matches

        except Exception as e:
            logger.error(f"Error querying Pinecone: {e}")
            return []

    def _match_with_mongodb(
        self,
        embedding: List[float],
        top_k: int = 1
    ) -> List[Dict[str, Any]]:
        """Match using MongoDB by computing similarity with stored embeddings.

        Args:
            embedding: Face embedding
            top_k: Number of top matches

        Returns:
            List of matches above confidence threshold
        """
        if not self.db:
            logger.error("Database not available for matching")
            return []

        try:
            people = self.db.list_all_known_people()
            matches = []

            for person in people:
                avg_embedding = person.get("average_embedding")
                if not avg_embedding:
                    continue

                # Compute cosine similarity
                similarity = self._cosine_similarity(embedding, avg_embedding)

                # Convert similarity to confidence score [0, 1]
                # Similarity is in [-1, 1], so convert to [0, 1]
                confidence = (similarity + 1) / 2

                if confidence >= self.confidence_threshold:
                    matches.append({
                        "person_id": str(person["_id"]),
                        "name": person["name"],
                        "confidence": confidence,
                        "linkedin_profile": person.get("linkedin_profile")
                    })

            # Sort by confidence and return top k
            matches.sort(key=lambda x: x["confidence"], reverse=True)
            logger.info(f"Found {len(matches)} matches above confidence {self.confidence_threshold}")
            return matches[:top_k]

        except Exception as e:
            logger.error(f"Error matching with MongoDB: {e}")
            return []

    def match_multiple_embeddings(
        self,
        embeddings: List[List[float]],
        use_pinecone: bool = True
    ) -> List[List[Dict[str, Any]]]:
        """Match multiple face embeddings.

        Args:
            embeddings: List of face embeddings
            use_pinecone: If True, use Pinecone for search

        Returns:
            List of match results, one per embedding
        """
        results = []
        for embedding in embeddings:
            matches = self.match_face_embedding(embedding, use_pinecone=use_pinecone)
            results.append(matches)
        return results

    def match_faces(
        self,
        detected_faces: List[Dict[str, Any]],
        use_pinecone: bool = True
    ) -> List[Dict[str, Any]]:
        """Match detected face objects against known people.

        This is a convenience method for CLI tools that works with detected_faces
        objects that contain embeddings and face detection info.

        Args:
            detected_faces: List of detected face objects with 'embedding' field
            use_pinecone: If True, use Pinecone for search

        Returns:
            List of match results aggregated from all detected faces
        """
        if not detected_faces:
            return []

        try:
            # Extract embeddings from detected faces
            embeddings = [face.get('embedding') for face in detected_faces if face.get('embedding') is not None]

            if not embeddings:
                logger.warning("No embeddings found in detected_faces")
                return []

            # Match all embeddings
            all_matches = self.match_multiple_embeddings(embeddings, use_pinecone=use_pinecone)

            # Aggregate unique matches (remove duplicates)
            unique_matches = {}
            for matches in all_matches:
                for match in matches:
                    person_id = match['person_id']
                    if person_id not in unique_matches or match['confidence'] > unique_matches[person_id]['confidence']:
                        unique_matches[person_id] = match

            # Return sorted by confidence
            result = sorted(unique_matches.values(), key=lambda x: x['confidence'], reverse=True)
            return result

        except Exception as e:
            logger.error(f"Error matching faces: {e}")
            return []

    def get_all_known_people(self) -> List[Dict[str, Any]]:
        """Get all known people from database.

        Returns:
            List of all known people with their metadata
        """
        if not self.db:
            logger.error("Database not available")
            return []

        try:
            people = self.db.list_all_known_people()
            result = []
            for person in people:
                result.append({
                    "person_id": str(person["_id"]),
                    "name": person["name"],
                    "linkedin_profile": person.get("linkedin_profile"),
                    "reference_photo_count": person.get("reference_photo_count", 0),
                    "metadata": person.get("metadata", {}),
                    "average_embedding": person.get("average_embedding")
                })
            return result
        except Exception as e:
            logger.error(f"Error retrieving known people: {e}")
            return []

    def find_gallery_faces_for_known_person(
        self,
        person_embedding: List[float],
        top_k: int = 1000,
        threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        REVERSE MATCHING: Query Pinecone with a known person's embedding
        to find similar gallery faces.

        This is the efficient approach - instead of iterating through all photos,
        we query Pinecone directly with the known person's averaged embedding.

        Args:
            person_embedding: The known person's averaged embedding (512 floats)
            top_k: Maximum number of similar faces to return
            threshold: Confidence threshold (default: self.confidence_threshold)

        Returns:
            List of matching gallery faces:
            [
                {
                    "pinecone_id": str,      # face_{photo_id}_{uuid}
                    "photo_id": str,
                    "confidence": float,
                    "metadata": dict
                }
            ]
        """
        if threshold is None:
            threshold = self.confidence_threshold

        if not self.pinecone_db:
            logger.error("Pinecone database not available for reverse matching")
            return []

        try:
            # Convert to list if numpy array
            if hasattr(person_embedding, 'tolist'):
                person_embedding = person_embedding.tolist()

            # Query Pinecone for similar gallery faces
            # Note: Gallery faces are stored WITHOUT a namespace (default namespace)
            results = self.pinecone_db.index.query(
                vector=person_embedding,
                top_k=top_k,
                include_metadata=True
                # No namespace - gallery faces are in default namespace
            )

            matches = []
            for match in results.get('matches', []):
                # Pinecone cosine similarity: -1 to 1, convert to 0 to 1
                raw_score = match.get('score', 0)
                confidence = (raw_score + 1.0) / 2.0

                if confidence >= threshold:
                    pinecone_id = match.get('id', '')
                    metadata = match.get('metadata', {})

                    # Extract photo_id from pinecone_id format: "face_{photo_id}_{uuid}"
                    photo_id = metadata.get('photo_id', '')
                    if not photo_id and pinecone_id.startswith('face_'):
                        # Parse from pinecone_id if not in metadata
                        parts = pinecone_id.split('_')
                        if len(parts) >= 2:
                            photo_id = parts[1]

                    matches.append({
                        "pinecone_id": pinecone_id,
                        "photo_id": photo_id,
                        "confidence": confidence,
                        "raw_score": raw_score,
                        "metadata": metadata
                    })

            logger.info(f"Found {len(matches)} gallery faces above threshold {threshold}")
            return matches

        except Exception as e:
            logger.error(f"Error in reverse matching query: {e}")
            return []

    def tag_all_known_people_in_gallery(
        self,
        mongo_db,
        top_k: int = 1000,
        threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        MAIN REVERSE MATCHING FUNCTION: For each known person, query Pinecone
        to find their matching gallery faces and update MongoDB.

        This is much faster than iterating through all photos because:
        - N queries (one per known person) vs N×M comparisons
        - Pinecone handles the similarity search efficiently

        Args:
            mongo_db: MongoDB database instance
            top_k: Max matches per known person
            threshold: Confidence threshold

        Returns:
            Summary of tagging results
        """
        if not self.db:
            logger.error("Known people database not available")
            return {"error": "Database not available"}

        if not self.pinecone_db:
            logger.error("Pinecone not available for reverse matching")
            return {"error": "Pinecone not available"}

        from datetime import datetime
        from bson import ObjectId

        results = {
            "total_known_people": 0,
            "people_with_matches": 0,
            "total_matches": 0,
            "new_matches_inserted": 0,
            "details": []
        }

        try:
            # Get all known people with their embeddings
            known_people = self.get_all_known_people()
            results["total_known_people"] = len(known_people)

            logger.info(f"Processing {len(known_people)} known people...")

            for person in known_people:
                person_name = person.get("name", "Unknown")
                person_id = person.get("person_id")
                linkedin_profile = person.get("linkedin_profile")
                avg_embedding = person.get("average_embedding")

                if not avg_embedding:
                    logger.warning(f"No embedding for {person_name}, skipping")
                    continue

                # Query Pinecone for similar gallery faces
                matches = self.find_gallery_faces_for_known_person(
                    person_embedding=avg_embedding,
                    top_k=top_k,
                    threshold=threshold
                )

                person_matches = 0
                person_new = 0

                for match in matches:
                    photo_id = match.get("photo_id")
                    if not photo_id:
                        continue

                    try:
                        photo_obj_id = ObjectId(photo_id)
                    except:
                        continue

                    # Get photo and find face_index from embedded faces array
                    photo = mongo_db['photos'].find_one({'_id': photo_obj_id})
                    if not photo:
                        continue

                    # Find face_index by matching pinecone_id in embedded faces array
                    face_index = None
                    for idx, face in enumerate(photo.get('faces', [])):
                        if face.get('pinecone_id') == match.get('pinecone_id'):
                            face_index = idx
                            break

                    if face_index is None:
                        continue

                    # Check for existing match in tagged_people array to avoid duplicates
                    tagged_people = photo.get('tagged_people', [])
                    existing_idx = None
                    for idx, tagged in enumerate(tagged_people):
                        if (tagged.get('person_id') == ObjectId(person_id) and
                            tagged.get('face_index') == face_index):
                            existing_idx = idx
                            break

                    if existing_idx is None:
                        # Insert new tagged person using $push
                        mongo_db['photos'].update_one(
                            {'_id': photo_obj_id},
                            {'$push': {
                                'tagged_people': {
                                    'person_id': ObjectId(person_id),
                                    'person_name': person_name,
                                    'face_index': face_index,
                                    'confidence': match['confidence'],
                                    'linkedin_profile': linkedin_profile,
                                    'created_at': datetime.utcnow()
                                }
                            }}
                        )
                        person_new += 1
                        results["new_matches_inserted"] += 1
                    else:
                        # Update confidence if higher using positional operator
                        if match['confidence'] > tagged_people[existing_idx].get('confidence', 0):
                            mongo_db['photos'].update_one(
                                {'_id': photo_obj_id},
                                {'$set': {
                                    f'tagged_people.{existing_idx}.confidence': match['confidence'],
                                    f'tagged_people.{existing_idx}.updated_at': datetime.utcnow()
                                }}
                            )

                    person_matches += 1

                results["total_matches"] += person_matches
                if person_matches > 0:
                    results["people_with_matches"] += 1

                results["details"].append({
                    "person_name": person_name,
                    "matches_found": person_matches,
                    "new_inserted": person_new
                })

                logger.info(f"  {person_name}: {person_matches} matches ({person_new} new)")

            logger.info(f"Tagging complete: {results['total_matches']} total matches, {results['new_matches_inserted']} new")
            return results

        except Exception as e:
            logger.error(f"Error in batch tagging: {e}")
            return {"error": str(e)}

    @staticmethod
    def _cosine_similarity(vec1: Any, vec2: Any) -> float:
        """Compute cosine similarity between two vectors.

        Args:
            vec1: First vector (list or numpy array)
            vec2: Second vector (list or numpy array)

        Returns:
            Cosine similarity score in range [-1, 1]
        """
        if isinstance(vec1, list):
            vec1 = np.array(vec1)
        if isinstance(vec2, list):
            vec2 = np.array(vec2)

        # Normalize vectors
        vec1_norm = vec1 / np.linalg.norm(vec1)
        vec2_norm = vec2 / np.linalg.norm(vec2)

        # Compute cosine similarity
        similarity = np.dot(vec1_norm, vec2_norm)
        return float(similarity)
