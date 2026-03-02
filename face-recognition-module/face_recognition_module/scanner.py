"""
Scanner for known faces folder to extract embeddings and index known people.
"""
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import cv2
import numpy as np
from . import config
from .database import KnownPeopleDB, create_known_person_document

logger = logging.getLogger(__name__)

# Supported image extensions
SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}


class FaceScanner:
    """Scanner to process known faces folder and generate embeddings."""

    def __init__(
        self,
        known_faces_dir: Optional[str] = None,
        db: Optional[KnownPeopleDB] = None,
        pinecone_db=None
    ):
        """Initialize the face scanner.

        Args:
            known_faces_dir: Path to known_faces directory. Defaults to config.KNOWN_FACES_DIR
            db: KnownPeopleDB instance for MongoDB operations
            pinecone_db: Optional Pinecone database for vector storage
        """
        self.known_faces_dir = Path(known_faces_dir or config.KNOWN_FACES_DIR)
        self.db = db
        self.pinecone_db = pinecone_db
        self.confidence_threshold = config.CONFIDENCE_THRESHOLD

        # Import and initialize face embedder
        try:
            from backend.core.face_recognition.face_embedder import FaceEmbedder
            self.embedder = FaceEmbedder()
        except ImportError:
            logger.warning("Could not import FaceEmbedder from backend. Ensure backend is in Python path.")
            self.embedder = None

    def scan_known_faces(self, update_existing: bool = False) -> Dict[str, Any]:
        """Scan the known_faces directory and index all people.

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
        if not self.embedder:
            logger.error("FaceEmbedder not available")
            return {
                "success": False,
                "total_people": 0,
                "processed_people": 0,
                "failed_people": 0,
                "errors": ["FaceEmbedder not available"]
            }

        if not self.known_faces_dir.exists():
            self.known_faces_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created known_faces directory: {self.known_faces_dir}")

        results = {
            "success": True,
            "total_people": 0,
            "processed_people": 0,
            "failed_people": 0,
            "errors": []
        }

        # Get all person directories
        person_dirs = [d for d in self.known_faces_dir.iterdir() if d.is_dir()]
        results["total_people"] = len(person_dirs)

        logger.info(f"Found {len(person_dirs)} people directories")

        for person_dir in sorted(person_dirs):
            try:
                self._process_person(person_dir, update_existing)
                results["processed_people"] += 1
            except Exception as e:
                error_msg = f"Failed to process {person_dir.name}: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
                results["failed_people"] += 1

        if results["failed_people"] > 0:
            results["success"] = False

        logger.info(
            f"Scan complete: {results['processed_people']}/{results['total_people']} "
            f"people processed successfully"
        )
        return results

    def _process_person(self, person_dir: Path, update_existing: bool = False) -> bool:
        """Process a single person directory.

        Args:
            person_dir: Path to person's directory
            update_existing: If True, update existing person entry

        Returns:
            True if processing was successful
        """
        person_name = person_dir.name
        logger.info(f"Processing person: {person_name}")

        # Get reference photos
        photo_files = self._get_valid_photos(person_dir)
        photo_count = len(photo_files)

        if photo_count == 0:
            raise ValueError(f"Person '{person_name}' has no valid photos.")

        # Extract embeddings from each photo
        embeddings = []
        valid_photos = []

        for photo_path in photo_files:
            try:
                embedding = self.embedder.get_single_face_embedding(str(photo_path))
                if embedding is not None:
                    embeddings.append(embedding)
                    valid_photos.append(str(photo_path))
                else:
                    logger.warning(f"No face found in {photo_path.name}")
            except Exception as e:
                logger.warning(f"Failed to extract embedding from {photo_path.name}: {e}")

        if not embeddings:
            raise ValueError(f"Could not extract any embeddings for '{person_name}'")

        # Compute average embedding
        average_embedding = np.mean(embeddings, axis=0).tolist()

        # Prepare person data
        person_data = create_known_person_document(
            name=person_name,
            average_embedding=average_embedding,
            individual_embeddings=[e.tolist() for e in embeddings],
            reference_photo_count=len(embeddings),
            linkedin_profile=None,  # Can be set separately if needed
            metadata={"reference_photos": valid_photos}
        )

        # Check if person already exists
        if self.db:
            existing_person = self.db.get_known_person_by_name(person_name)

            if existing_person:
                if update_existing:
                    logger.info(f"Updating existing person: {person_name}")
                    self.db.update_known_person(
                        existing_person["_id"],
                        {
                            "average_embedding": average_embedding,
                            "individual_embeddings": person_data["individual_embeddings"],
                            "reference_photo_count": len(embeddings),
                            "metadata": person_data["metadata"]
                        }
                    )
                    person_id = existing_person["_id"]
                else:
                    raise ValueError(f"Person '{person_name}' already exists. Use update_existing=True to update.")
            else:
                # Insert new person
                logger.info(f"Inserting new person: {person_name}")
                person_id = self.db.insert_known_person(person_data)
        else:
            person_id = None
            logger.warning("Database not available. Skipping MongoDB insertion.")

        # Upload to Pinecone if available
        if self.pinecone_db and person_id:
            try:
                self.pinecone_db.upsert(
                    vectors=[
                        (
                            str(person_id),
                            average_embedding,
                            {"person_name": person_name, "person_id": str(person_id)}
                        )
                    ],
                    namespace=config.PINECONE_NAMESPACE_KNOWN
                )
                logger.info(f"Uploaded {person_name} to Pinecone")

                # Update person document with Pinecone ID
                if self.db:
                    self.db.update_known_person(
                        person_id,
                        {"pinecone_id": str(person_id)}
                    )
            except Exception as e:
                logger.warning(f"Failed to upload {person_name} to Pinecone: {e}")

        logger.info(
            f"[OK] Successfully processed {person_name}: "
            f"{len(embeddings)} embeddings, avg_embedding_dim={len(average_embedding)}"
        )
        return True

    def _get_valid_photos(self, person_dir: Path) -> List[Path]:
        """Get all valid photo files from a person's directory.

        Args:
            person_dir: Path to person's directory

        Returns:
            List of Path objects for valid image files
        """
        valid_files = []
        for file in sorted(person_dir.iterdir()):
            if file.is_file() and file.suffix.lower() in SUPPORTED_EXTENSIONS:
                valid_files.append(file)
        return valid_files

    def add_person(
        self,
        person_name: str,
        photo_paths: List[str],
        linkedin_profile: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add a single person to the database.

        Args:
            person_name: Name of the person
            photo_paths: List of paths to reference photos (at least 1 required)
            linkedin_profile: Optional LinkedIn profile URL
            metadata: Optional additional metadata

        Returns:
            True if successfully added
        """
        if len(photo_paths) == 0:
            raise ValueError("At least one photo is required.")

        # Extract embeddings
        embeddings = []
        valid_photos = []

        for photo_path in photo_paths:
            path = Path(photo_path)
            if not path.exists():
                logger.warning(f"Photo not found: {photo_path}")
                continue

            try:
                embedding = self.embedder.get_single_face_embedding(str(path))
                if embedding is not None:
                    embeddings.append(embedding)
                    valid_photos.append(str(path))
            except Exception as e:
                logger.warning(f"Failed to extract embedding from {path}: {e}")

        if not embeddings:
            raise ValueError(f"Could not extract embeddings from any photos for '{person_name}'")

        # Compute average embedding
        average_embedding = np.mean(embeddings, axis=0).tolist()

        # Create person document
        person_data = create_known_person_document(
            name=person_name,
            average_embedding=average_embedding,
            individual_embeddings=[e.tolist() for e in embeddings],
            reference_photo_count=len(embeddings),
            linkedin_profile=linkedin_profile,
            metadata=metadata or {"reference_photos": valid_photos}
        )

        # Insert into database
        if self.db:
            try:
                person_id = self.db.insert_known_person(person_data)

                # Upload to Pinecone
                if self.pinecone_db:
                    self.pinecone_db.upsert(
                        vectors=[
                            (
                                str(person_id),
                                average_embedding,
                                {"person_name": person_name, "person_id": str(person_id)}
                            )
                        ],
                        namespace=config.PINECONE_NAMESPACE_KNOWN
                    )

                    # Update with Pinecone ID
                    self.db.update_known_person(
                        person_id,
                        {"pinecone_id": str(person_id)}
                    )

                logger.info(f"Successfully added person: {person_name}")
                return True
            except Exception as e:
                logger.error(f"Failed to add person: {e}")
                raise

        return False
