"""
Debug script to check gallery data in database
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymongo import MongoClient
from backend.config.settings import get_settings
import json

def check_galleries():
    # Connect to MongoDB
    settings = get_settings()
    client = MongoClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DB_NAME]

    # Get all galleries
    galleries = list(db.galleries.find())

    print(f"Found {len(galleries)} galleries in database:\n")

    for gallery in galleries:
        print(f"Gallery ID: {gallery.get('_id')}")
        print(f"  Share Token: {gallery.get('share_token')}")
        print(f"  Name: {gallery.get('name', 'Untitled')}")
        print(f"  host_user_id exists: {'host_user_id' in gallery}")
        print(f"  host_user_id value: {gallery.get('host_user_id', 'NOT SET')}")
        print(f"  host_user_id type: {type(gallery.get('host_user_id'))}")
        print(f"  All keys: {list(gallery.keys())}")

        # Test prepare_document_for_response
        from backend.models.database import prepare_document_for_response
        prepared = prepare_document_for_response(gallery)
        print(f"\n  After prepare_document_for_response:")
        print(f"    host_user_id: {prepared.get('host_user_id', 'NOT SET')}")
        print(f"    host_user_id type: {type(prepared.get('host_user_id'))}")
        print(f"    All keys: {list(prepared.keys())}")
        print()

    client.close()

if __name__ == "__main__":
    check_galleries()
