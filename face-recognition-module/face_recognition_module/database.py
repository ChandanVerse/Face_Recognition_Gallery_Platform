"""
MongoDB database operations for known people management.
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId
import pymongo
from pymongo import MongoClient
from . import config

logger = logging.getLogger(__name__)

# Collection names
KNOWN_PEOPLE = "known_people"


def create_known_person_document(
    name: str,
    average_embedding: List[float],
    individual_embeddings: List[List[float]],
    linkedin_profile: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    reference_photo_count: int = 0,
    pinecone_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a known person document for MongoDB."""
    return {
        "name": name,
        "linkedin_profile": linkedin_profile,
        "metadata": metadata or {},
        "reference_photo_count": reference_photo_count,
        "average_embedding": average_embedding,
        "individual_embeddings": individual_embeddings,
        "pinecone_id": pinecone_id,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }


class KnownPeopleDB:
    """Database operations for known people collection."""

    def __init__(self, mongodb_url: Optional[str] = None, db_name: Optional[str] = None):
        """Initialize database connection.

        Args:
            mongodb_url: MongoDB connection URL. Defaults to config.MONGODB_URL
            db_name: Database name. Defaults to config.MONGODB_DB
        """
        self.mongodb_url = mongodb_url or config.MONGODB_URL
        self.db_name = db_name or config.MONGODB_DB
        self.client = None
        self.db = None
        self.collection = None

    def connect(self):
        """Establish MongoDB connection."""
        try:
            self.client = MongoClient(self.mongodb_url)
            self.db = self.client[self.db_name]
            self.collection = self.db[KNOWN_PEOPLE]

            # Create indexes
            self._create_indexes()

            logger.info("Connected to MongoDB successfully")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    def disconnect(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")

    def _create_indexes(self):
        """Create necessary indexes on the collection."""
        try:
            # Index on name for quick lookups
            self.collection.create_index("name", unique=True)
            # Index on created_at for sorting
            self.collection.create_index("created_at")
            logger.info("Indexes created successfully")
        except Exception as e:
            logger.warning(f"Error creating indexes: {e}")

    def insert_known_person(self, person_data: Dict[str, Any]) -> ObjectId:
        """Insert a new known person into the database.

        Args:
            person_data: Dictionary containing person information

        Returns:
            ObjectId of the inserted document
        """
        try:
            result = self.collection.insert_one(person_data)
            logger.info(f"Inserted known person: {person_data['name']} with ID {result.inserted_id}")
            return result.inserted_id
        except pymongo.errors.DuplicateKeyError:
            logger.warning(f"Person '{person_data['name']}' already exists")
            raise
        except Exception as e:
            logger.error(f"Error inserting known person: {e}")
            raise

    def update_known_person(
        self,
        person_id: ObjectId,
        update_data: Dict[str, Any]
    ) -> bool:
        """Update an existing known person.

        Args:
            person_id: ObjectId of the person to update
            update_data: Dictionary with fields to update

        Returns:
            True if update was successful
        """
        try:
            update_data["updated_at"] = datetime.utcnow()
            result = self.collection.update_one(
                {"_id": person_id},
                {"$set": update_data}
            )
            if result.modified_count > 0:
                logger.info(f"Updated known person with ID {person_id}")
                return True
            else:
                logger.warning(f"No document found with ID {person_id}")
                return False
        except Exception as e:
            logger.error(f"Error updating known person: {e}")
            raise

    def get_known_person_by_id(self, person_id: ObjectId) -> Optional[Dict[str, Any]]:
        """Retrieve a known person by ID.

        Args:
            person_id: ObjectId of the person

        Returns:
            Dictionary containing person data, or None if not found
        """
        try:
            person = self.collection.find_one({"_id": person_id})
            return person
        except Exception as e:
            logger.error(f"Error retrieving known person: {e}")
            raise

    def get_known_person_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Retrieve a known person by name.

        Args:
            name: Name of the person

        Returns:
            Dictionary containing person data, or None if not found
        """
        try:
            person = self.collection.find_one({"name": name})
            return person
        except Exception as e:
            logger.error(f"Error retrieving known person by name: {e}")
            raise

    def list_all_known_people(self) -> List[Dict[str, Any]]:
        """Retrieve all known people.

        Returns:
            List of dictionaries containing person data
        """
        try:
            people = list(self.collection.find().sort("name", 1))
            logger.info(f"Retrieved {len(people)} known people")
            return people
        except Exception as e:
            logger.error(f"Error retrieving known people: {e}")
            raise

    def delete_known_person(self, person_id: ObjectId) -> bool:
        """Delete a known person from the database.

        Args:
            person_id: ObjectId of the person to delete

        Returns:
            True if deletion was successful
        """
        try:
            result = self.collection.delete_one({"_id": person_id})
            if result.deleted_count > 0:
                logger.info(f"Deleted known person with ID {person_id}")
                return True
            else:
                logger.warning(f"No document found with ID {person_id}")
                return False
        except Exception as e:
            logger.error(f"Error deleting known person: {e}")
            raise

    def get_person_embeddings(self, person_id: ObjectId) -> Optional[List[float]]:
        """Get the average embedding for a known person.

        Args:
            person_id: ObjectId of the person

        Returns:
            List of 512 float values representing the embedding
        """
        try:
            person = self.collection.find_one(
                {"_id": person_id},
                {"average_embedding": 1}
            )
            if person:
                return person.get("average_embedding")
            return None
        except Exception as e:
            logger.error(f"Error retrieving person embeddings: {e}")
            raise

    def count_known_people(self) -> int:
        """Count total number of known people in database.

        Returns:
            Number of known people
        """
        try:
            count = self.collection.count_documents({})
            return count
        except Exception as e:
            logger.error(f"Error counting known people: {e}")
            raise

    def check_person_exists(self, name: str) -> bool:
        """Check if a person with given name already exists.

        Args:
            name: Name of the person

        Returns:
            True if person exists, False otherwise
        """
        try:
            return self.collection.find_one({"name": name}) is not None
        except Exception as e:
            logger.error(f"Error checking person existence: {e}")
            raise
