#!/usr/bin/env python3
"""
Database Reset Script
Clears all data from MongoDB database and Pinecone vector database
Also clears Python cache to ensure fresh settings are loaded
"""
import sys
import os
import shutil
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from backend.config.settings import get_settings
from backend.config.database import get_database, close_database_connection
from backend.models.database import (
    USERS, USER_PROFILES, REFERENCE_PHOTOS, GALLERIES,
    PHOTOS, FACES, USER_PHOTO_ASSOCIATIONS
)

settings = get_settings()


def reset_mongodb():
    """Drop all MongoDB collections"""
    print("\n" + "="*60)
    print("Resetting MongoDB Database")
    print("="*60)

    try:
        db = get_database()

        # List all collections to drop
        collections = [USERS, USER_PROFILES, REFERENCE_PHOTOS, GALLERIES,
                      PHOTOS, FACES, USER_PHOTO_ASSOCIATIONS]

        # Get document counts before deletion
        print("Current collection counts:")
        total_docs = 0
        for collection_name in collections:
            count = db[collection_name].count_documents({})
            if count > 0:
                print(f"  - {collection_name}: {count} documents")
                total_docs += count

        if total_docs == 0:
            print("[OK] All collections are already empty")
            return True

        print(f"\nTotal documents to delete: {total_docs}")
        print("Dropping all collections...")

        # Drop each collection
        deleted_count = 0
        for collection_name in collections:
            count = db[collection_name].count_documents({})
            if count > 0:
                db[collection_name].drop()
                deleted_count += count
                print(f"[OK] Dropped {collection_name} ({count} documents)")

        print(f"\n[OK] Successfully deleted {deleted_count} documents from {len(collections)} collections")

        # Recreate indexes
        print("\nRecreating indexes...")
        from backend.config.database import initialize_indexes
        initialize_indexes()

        return True

    except Exception as e:
        print(f"[ERROR] Error resetting MongoDB: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        close_database_connection()


def reset_pinecone():
    """Clear all vectors from Pinecone index"""
    print("\n" + "="*60)
    print("Resetting Pinecone Vector Database")
    print("="*60)

    if not settings.PINECONE_API_KEY or settings.PINECONE_API_KEY == "your_pinecone_api_key_here":
        print("[WARN] Pinecone not configured - skipping")
        return True

    try:
        from pinecone import Pinecone

        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        index = pc.Index(settings.PINECONE_INDEX_NAME)

        # Get stats before deletion
        stats = index.describe_index_stats()
        total_vectors = stats.total_vector_count

        if total_vectors == 0:
            print("[OK] Pinecone index is already empty")
            return True

        print(f"Found {total_vectors} vectors in index '{settings.PINECONE_INDEX_NAME}'")
        print("Deleting all vectors...")

        # Delete all vectors
        index.delete(delete_all=True)

        # Verify deletion
        stats = index.describe_index_stats()
        remaining = stats.total_vector_count

        if remaining == 0:
            print(f"[OK] Successfully deleted all {total_vectors} vectors")
            return True
        else:
            print(f"[WARN] Warning: {remaining} vectors still remain")
            return False

    except Exception as e:
        print(f"[ERROR] Error resetting Pinecone: {e}")
        return False


def clear_storage():
    """Clear all uploaded files from local storage"""
    print("\n" + "="*60)
    print("Clearing Local Storage")
    print("="*60)

    storage_path = Path(settings.STORAGE_BASE_PATH)

    if not storage_path.exists():
        print("[OK] Storage directory doesn't exist - nothing to clear")
        return True

    try:
        deleted_count = 0

        # Delete all files in galleries
        galleries_dir = storage_path / "galleries"
        if galleries_dir.exists():
            for item in galleries_dir.rglob('*'):
                if item.is_file():
                    item.unlink()
                    deleted_count += 1
            # Remove empty directories
            for item in sorted(galleries_dir.rglob('*'), reverse=True):
                if item.is_dir() and not any(item.iterdir()):
                    item.rmdir()
            print(f"[OK] Cleared galleries/ - deleted {deleted_count} files")

        # Delete all files in reference_photos
        ref_count = 0
        reference_dir = storage_path / "reference_photos"
        if reference_dir.exists():
            for item in reference_dir.rglob('*'):
                if item.is_file():
                    item.unlink()
                    ref_count += 1
            # Remove empty directories
            for item in sorted(reference_dir.rglob('*'), reverse=True):
                if item.is_dir() and not any(item.iterdir()):
                    item.rmdir()
            print(f"[OK] Cleared reference_photos/ - deleted {ref_count} files")

        total_deleted = deleted_count + ref_count
        if total_deleted == 0:
            print("[OK] No files to delete - storage is already empty")

        return True

    except Exception as e:
        print(f"[ERROR] Error clearing storage: {e}")
        return False


def clear_python_cache():
    """Clear all Python __pycache__ directories and .pyc files"""
    print("\n" + "="*60)
    print("Clearing Python Cache")
    print("="*60)

    project_root = Path(__file__).parent

    try:
        cache_dirs_deleted = 0
        pyc_files_deleted = 0

        # Find and delete all __pycache__ directories
        for cache_dir in project_root.rglob('__pycache__'):
            if cache_dir.is_dir():
                shutil.rmtree(cache_dir)
                cache_dirs_deleted += 1

        # Find and delete any remaining .pyc files
        for pyc_file in project_root.rglob('*.pyc'):
            if pyc_file.is_file():
                pyc_file.unlink()
                pyc_files_deleted += 1

        # Clear pydantic settings cache
        get_settings.cache_clear()
        print("[OK] Cleared pydantic settings cache")

        if cache_dirs_deleted == 0 and pyc_files_deleted == 0:
            print("[OK] No Python cache to clear")
        else:
            print(f"[OK] Deleted {cache_dirs_deleted} __pycache__ directories")
            print(f"[OK] Deleted {pyc_files_deleted} .pyc files")

        return True

    except Exception as e:
        print(f"[ERROR] Error clearing Python cache: {e}")
        return False


def clear_redis():
    """Clear all Redis data (Celery tasks)"""
    print("\n" + "="*60)
    print("Clearing Redis Cache")
    print("="*60)

    try:
        import redis

        r = redis.from_url(settings.REDIS_URL)

        # Get stats before clearing
        db_size = r.dbsize()

        if db_size == 0:
            print("[OK] Redis is already empty")
            return True

        print(f"Found {db_size} keys in Redis")
        print("Flushing database...")

        r.flushdb()

        print(f"[OK] Successfully cleared all {db_size} keys")
        return True

    except Exception as e:
        print(f"[ERROR] Error clearing Redis: {e}")
        print("  Make sure Redis is running")
        return False


def main():
    print("\n" + "="*60)
    print("DATABASE RESET SCRIPT")
    print("="*60)
    print("\n[WARNING] This will DELETE ALL DATA!")
    print("  - All MongoDB collections")
    print("  - All Pinecone vectors")
    print("  - All uploaded files")
    print("  - All Redis cache")
    print("  - All Python cache (__pycache__)")
    print("\n" + "="*60)

    # Confirm
    response = input("\nAre you sure you want to continue? (type 'yes' to confirm): ")
    if response.lower() != 'yes':
        print("\n[CANCELLED] Reset cancelled")
        return

    print("\n[INFO] Starting reset process...\n")

    results = []

    # Clear Python cache first (important for fresh settings)
    results.append(("Python Cache", clear_python_cache()))

    # Reset MongoDB
    results.append(("MongoDB", reset_mongodb()))

    # Reset Pinecone
    results.append(("Pinecone", reset_pinecone()))

    # Clear local storage
    results.append(("Local Storage", clear_storage()))

    # Clear Redis
    results.append(("Redis", clear_redis()))

    # Summary
    print("\n" + "="*60)
    print("RESET SUMMARY")
    print("="*60)

    for name, success in results:
        status = "[OK] SUCCESS" if success else "[X] FAILED"
        print(f"{status}: {name}")

    all_success = all(success for _, success in results)

    if all_success:
        print("\n[SUCCESS] Database reset complete! All data cleared.")
        print("\n[INFO] Next steps:")
        print("   1. Start the backend: python run.py")
        print("   2. Start Celery: python backend/start_celery.py")
        print("   3. Start the frontend: python frontend/start_frontend.py")
        print("   4. Register a new user through the frontend")
        print("   5. Upload photos to test")
    else:
        print("\n[WARN] Reset completed with some errors. Check the output above.")

    print("="*60 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[X] Reset cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[X] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
