"""
Configuration for the Face Recognition Module.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Paths
# BASE_DIR points to face-recognition-module folder
BASE_DIR = Path(__file__).resolve().parent.parent
# PROJECT_ROOT points to the main project folder (parent of face-recognition-module)
PROJECT_ROOT = BASE_DIR.parent
# known_faces directory is at project root level
KNOWN_FACES_DIR = os.getenv("KNOWN_FACES_DIR", str(PROJECT_ROOT / "known_faces"))
STORAGE_DIR = os.getenv("STORAGE_DIR", str(PROJECT_ROOT / "storage"))

# MongoDB Configuration
# Try both naming conventions (MONGODB_URL or MONGODB_URI)
MONGODB_URL = os.getenv("MONGODB_URL") or os.getenv("MONGODB_URI", "mongodb+srv://user:password@cluster.mongodb.net/")
# Try both naming conventions (MONGODB_DB or MONGODB_DB_NAME)
MONGODB_DB = os.getenv("MONGODB_DB") or os.getenv("MONGODB_DB_NAME", "aiGallery")

# Face Recognition Configuration
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))

# InsightFace Configuration
INSIGHTFACE_MODEL = os.getenv("INSIGHTFACE_MODEL", "buffalo_l")
DETECTION_SIZE = int(os.getenv("DETECTION_SIZE", "1024"))
GPU_ENABLED = os.getenv("GPU_ENABLED", "true").lower() == "true"

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Feature Flags
PINECONE_ENABLED = os.getenv("PINECONE_ENABLED", "true").lower() == "true"
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "face-embeddings-webapp")
PINECONE_NAMESPACE_KNOWN = "known_people"
