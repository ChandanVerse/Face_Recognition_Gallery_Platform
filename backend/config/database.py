"""
MongoDB database connection and session management
"""
from pymongo import MongoClient
from pymongo.database import Database
from contextlib import contextmanager
from typing import Generator
import logging

from backend.config.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Create MongoDB client
client = None
db = None


def get_database() -> Database:
    """Get MongoDB database instance"""
    global client, db

    if db is None:
        try:
            client = MongoClient(settings.MONGODB_URI)
            db = client[settings.MONGODB_DB_NAME]

            # Test connection
            client.admin.command('ping')
            logger.info(f"[OK] Connected to MongoDB: {settings.MONGODB_DB_NAME}")

        except Exception as e:
            logger.error(f"[ERROR] Failed to connect to MongoDB: {e}")
            raise

    return db


def get_db() -> Generator[Database, None, None]:
    """
    Dependency for FastAPI routes to get database session

    Usage:
        @app.get("/items")
        def get_items(db: Database = Depends(get_db)):
            return list(db.items.find())
    """
    database = get_database()
    try:
        yield database
    finally:
        pass  # MongoDB connections are managed globally


@contextmanager
def get_db_context():
    """
    Context manager for database sessions (for use in workers/scripts)

    Usage:
        with get_db_context() as db:
            user = db.users.find_one({"_id": user_id})
    """
    database = get_database()
    try:
        yield database
    except Exception as e:
        logger.error(f"Database error: {e}")
        raise


def close_database_connection():
    """Close MongoDB connection"""
    global client, db
    if client:
        client.close()
        logger.info("[OK] MongoDB connection closed")
        client = None
        db = None


# Initialize indexes for better query performance
def initialize_indexes():
    """Create indexes for MongoDB collections"""
    database = get_database()

    # Users collection
    database.users.create_index("email", unique=True)

    # Galleries collection
    database.galleries.create_index("host_user_id")
    database.galleries.create_index("share_token", unique=True)

    # Photos collection (with multikey indexes for embedded arrays)
    database.photos.create_index("gallery_id")
    database.photos.create_index("faces.pinecone_id")  # Multikey index for embedded faces
    database.photos.create_index("matched_users.user_id")  # Multikey index for user photo lookups
    database.photos.create_index("tagged_people.person_id")  # Multikey index for known people

    # Known people collection
    database.known_people.create_index("name", unique=True)

    logger.info("[OK] MongoDB indexes initialized")
