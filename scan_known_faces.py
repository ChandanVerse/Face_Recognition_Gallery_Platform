#!/usr/bin/env python3
"""
CLI tool to scan the known_faces directory and index all known people.
Also supports batch reprocessing of gallery photos to tag known people.

Usage:
    python3 scan_known_faces.py                        # Scan all people
    python3 scan_known_faces.py --scan --reprocess-all # Scan + reprocess all photos
    python3 scan_known_faces.py --reprocess-only       # Reprocess all photos (skip scan)
    python3 scan_known_faces.py --list                 # List all known people
"""

import argparse
import logging
import sys
import os
import json
from pathlib import Path
import numpy as np
from datetime import datetime

from face_recognition_module import FaceScanner
from face_recognition_module.database import KnownPeopleDB
from face_recognition_module import config

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def list_known_people():
    """List all known people in the database."""
    try:
        db = KnownPeopleDB()
        db.connect()

        people = db.list_all_known_people()

        if not people:
            print("No known people in database.")
            return True

        print(f"\n{'Name':<30} {'Role':<30} {'Photos':<8} {'ID':<24}")
        print("-" * 92)

        for person in people:
            name = person.get('name', 'Unknown')[:30]
            role = (person.get('role') or 'N/A')[:30]
            photo_count = person.get('reference_photo_count', 0)
            person_id = str(person['_id'])[:24]

            print(f"{name:<30} {role:<30} {photo_count:<8} {person_id:<24}")

        print(f"\nTotal: {len(people)} known people")
        print("(No minimum/maximum photo constraints - at least 1 photo required)")
        return True

    except Exception as e:
        logger.error(f"Error listing known people: {e}")
        return False
    finally:
        if 'db' in locals():
            db.disconnect()


def scan_known_faces(update_existing=False):
    """Scan the known_faces directory and index all people (synchronous)."""
    try:
        db = KnownPeopleDB()
        db.connect()

        scanner = FaceScanner(db=db)

        print(f"\nScanning known_faces directory: {scanner.known_faces_dir}")
        print("-" * 80)

        results = scanner.scan_known_faces(update_existing=update_existing)

        print("\n" + "=" * 80)
        print("SCAN RESULTS")
        print("=" * 80)
        print(f"Total people found:      {results['total_people']}")
        print(f"Successfully processed:  {results['processed_people']}")
        print(f"Failed:                  {results['failed_people']}")

        if results['errors']:
            print("\nErrors:")
            for error in results['errors']:
                print(f"  - {error}")

        print("=" * 80)

        return results['success']

    except Exception as e:
        logger.error(f"Error scanning known faces: {e}")
        return False
    finally:
        if 'db' in locals():
            db.disconnect()


def reprocess_all_photos():
    """
    Tag known people in gallery using REVERSE MATCHING.

    Instead of iterating through all photos (slow), this queries Pinecone
    with each known person's embedding to find their matching gallery faces.

    Flow:
    1. Get all known people with their averaged embeddings
    2. For each known person, query Pinecone for similar gallery faces
    3. Update MongoDB with matches

    This is much faster: N queries (one per known person) vs N*M comparisons.
    """
    try:
        from backend.config.database import get_database
        from backend.core.database.pinecone_db import PineconeDatabase
        from backend.config.settings import get_settings
        from face_recognition_module import FaceMatcher

        print("\n" + "="*80)
        print("REVERSE MATCHING: Tag Known People in Gallery")
        print("="*80)
        print("This queries Pinecone with each known person's embedding")
        print("to find their matching photos (much faster than photo-by-photo)")
        print("-" * 80)

        # Get MongoDB database and settings
        mongo_db = get_database()
        settings = get_settings()

        # Initialize Pinecone - REQUIRED for reverse matching
        try:
            pinecone_db = PineconeDatabase(
                api_key=settings.PINECONE_API_KEY,
                index_name=settings.PINECONE_INDEX_NAME,
                environment=settings.PINECONE_ENVIRONMENT
            )
            print("[OK] Connected to Pinecone")
        except Exception as e:
            print(f"[ERROR] Pinecone is required for reverse matching: {e}")
            return False

        # Initialize known people database
        known_people_db = KnownPeopleDB()
        known_people_db.connect()

        try:
            # Create indexes for efficient duplicate checking
            mongo_db['known_faces_matches'].create_index([('photo_id', 1)])
            mongo_db['known_faces_matches'].create_index([('photo_id', 1), ('person_id', 1), ('person_name', 1)])

            # Initialize matcher with both databases
            matcher = FaceMatcher(
                db=known_people_db,
                pinecone_db=pinecone_db,
                confidence_threshold=0.7  # 70% confidence threshold
            )

            # Get count of known people
            known_people = known_people_db.list_all_known_people()
            print(f"\n[INFO] Found {len(known_people)} known people to match")
            print(f"[INFO] Querying Pinecone for each person's matches...\n")

            # Run reverse matching - this does all the work
            results = matcher.tag_all_known_people_in_gallery(
                mongo_db=mongo_db,
                top_k=1000,  # Get up to 1000 matches per person
                threshold=0.7
            )

            # Print results
            print(f"\n{'='*80}")
            print("TAGGING COMPLETE")
            print("="*80)

            if "error" in results:
                print(f"[ERROR] {results['error']}")
                return False

            print(f"  Known people processed: {results.get('total_known_people', 0)}")
            print(f"  People with matches:    {results.get('people_with_matches', 0)}")
            print(f"  Total matches found:    {results.get('total_matches', 0)}")
            print(f"  New matches inserted:   {results.get('new_matches_inserted', 0)}")

            # Print per-person details
            details = results.get('details', [])
            if details:
                print(f"\n{'Person':<30} {'Matches':<12} {'New':<10}")
                print("-" * 52)
                for d in details:
                    print(f"{d['person_name']:<30} {d['matches_found']:<12} {d['new_inserted']:<10}")

            print("="*80)
            return True

        finally:
            known_people_db.disconnect()

    except Exception as e:
        logger.error(f"Error reprocessing photos: {e}")
        print(f"Error: {e}")
        return False


def scan_known_faces_async(update_existing=False):
    """Scan known_faces folder in background using Celery."""
    try:
        from backend.workers.celery_app import celery_app

        print("\nSubmitting scan task to Celery...")
        task = celery_app.send_task('face_recognition_module.scan_known_faces_task', args=(update_existing,))

        print(f"Task submitted successfully!")
        print(f"Task ID: {task.id}")
        return True
    except ImportError:
        print("Error: Celery tasks not available. Make sure backend is configured.")
        logger.error("Could not import backend celery_app")
        return False
    except Exception as e:
        logger.error(f"Error submitting scan task: {e}")
        print(f"Error: {e}")
        return False


def reprocess_all_photos_async():
    """Reprocess all photos to tag known people using Celery."""
    try:
        from backend.workers.celery_app import celery_app

        print("\nSubmitting batch reprocessing task to Celery...")
        task = celery_app.send_task('face_recognition_module.reprocess_all_photos_task')

        print(f"Task submitted successfully!")
        print(f"Task ID: {task.id}")
        print(f"\nThis will reprocess all existing gallery photos and tag known people.")
        return True
    except ImportError:
        print("Error: Celery tasks not available. Make sure backend is configured.")
        logger.error("Could not import backend celery_app")
        return False
    except Exception as e:
        logger.error(f"Error submitting reprocess task: {e}")
        print(f"Error: {e}")
        return False


def scan_and_reprocess_all_async(update_existing=False):
    """Scan known_faces and then reprocess all photos using Celery orchestrator."""
    try:
        from backend.workers.celery_app import celery_app

        print("\nSubmitting scan + reprocess task to Celery...")
        print("This will:")
        print("  1. Scan known_faces folder and index people")
        print("  2. Automatically reprocess all existing gallery photos")
        print("  3. Tag known people in all photos")
        print()

        task = celery_app.send_task('face_recognition_module.scan_and_reprocess_all_task', args=(update_existing,))

        print(f"Task submitted successfully!")
        print(f"Task ID: {task.id}")
        return True
    except ImportError:
        print("Error: Celery tasks not available. Make sure backend is configured.")
        logger.error("Could not import backend celery_app")
        return False
    except Exception as e:
        logger.error(f"Error submitting orchestrator task: {e}")
        print(f"Error: {e}")
        return False


def delete_person(person_name):
    """Delete a known person from the database."""
    try:
        db = KnownPeopleDB()
        db.connect()

        person = db.get_known_person_by_name(person_name)

        if not person:
            print(f"Person '{person_name}' not found in database.")
            return False

        # Confirm deletion
        response = input(f"Delete '{person_name}'? (yes/no): ").strip().lower()
        if response != 'yes':
            print("Deletion cancelled.")
            return False

        success = db.delete_known_person(person["_id"])

        if success:
            print(f"Successfully deleted '{person_name}'")
        else:
            print(f"Failed to delete '{person_name}'")

        return success

    except Exception as e:
        logger.error(f"Error deleting person: {e}")
        return False
    finally:
        if 'db' in locals():
            db.disconnect()


def update_person_info(person_name, role=None, metadata=None):
    """Update a known person's metadata."""
    try:
        db = KnownPeopleDB()
        db.connect()

        person = db.get_known_person_by_name(person_name)

        if not person:
            print(f"Person '{person_name}' not found in database.")
            return False

        update_data = {}
        if role is not None:
            update_data['role'] = role
        if metadata is not None:
            update_data['metadata'] = metadata

        if not update_data:
            print("No updates provided.")
            return False

        success = db.update_known_person(person["_id"], update_data)

        if success:
            print(f"Successfully updated '{person_name}'")
        else:
            print(f"Failed to update '{person_name}'")

        return success

    except Exception as e:
        logger.error(f"Error updating person: {e}")
        return False
    finally:
        if 'db' in locals():
            db.disconnect()


def main():
    parser = argparse.ArgumentParser(
        description="Manage known people for face recognition system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scan_known_faces.py                           # Scan all people (sync)
  python3 scan_known_faces.py --scan --async            # Scan in background (async)
  python3 scan_known_faces.py --scan --reprocess-all    # Scan + reprocess all photos
  python3 scan_known_faces.py --reprocess-only          # Only reprocess photos (skip scan)
  python3 scan_known_faces.py --reprocess-only --async  # Reprocess in background
  python3 scan_known_faces.py --update                  # Update existing people
  python3 scan_known_faces.py --list                    # List all known people
  python3 scan_known_faces.py --delete John             # Delete person
  python3 scan_known_faces.py --update-info John --role Manager  # Update role
        """
    )

    parser.add_argument('--scan', action='store_true', help='Scan and index known faces')
    parser.add_argument('--update', action='store_true', help='Scan and update existing people')
    parser.add_argument('--list', action='store_true', help='List all known people')
    parser.add_argument('--delete', type=str, metavar='NAME', help='Delete a known person')
    parser.add_argument('--update-info', type=str, metavar='NAME', help='Update person info')
    parser.add_argument('--role', type=str, help='Role/title for person')
    parser.add_argument('--metadata', type=str, help='JSON metadata for person')

    # Celery task options
    parser.add_argument('--async', action='store_true', dest='async_task',
                        help='Run scan/reprocess as background Celery task (async)')
    parser.add_argument('--reprocess-all', action='store_true',
                        help='After scanning, reprocess all gallery photos to tag known people')
    parser.add_argument('--reprocess-only', action='store_true',
                        help='Only reprocess gallery photos (skip scanning known_faces). Use this when known people are already indexed.')

    args = parser.parse_args()

    # If no arguments provided, default to scan
    if not any([args.scan, args.update, args.list, args.delete, args.update_info, args.reprocess_only]):
        args.scan = True

    success = True

    try:
        if args.list:
            success = list_known_people()
        elif args.delete:
            success = delete_person(args.delete)
        elif args.reprocess_only:
            # Only reprocess photos without scanning known_faces
            if args.async_task:
                success = reprocess_all_photos_async()
            else:
                success = reprocess_all_photos()
        elif args.update_info:
            metadata = None
            if args.metadata:
                try:
                    metadata = json.loads(args.metadata)
                except json.JSONDecodeError:
                    print("Invalid JSON in --metadata")
                    return 1
            success = update_person_info(args.update_info, role=args.role, metadata=metadata)
        elif args.update:
            if args.async_task:
                success = scan_known_faces_async(update_existing=True)
            else:
                success = scan_known_faces(update_existing=True)
        elif args.scan:
            # Handle scan with optional reprocessing
            if args.reprocess_all:
                # Scan + Reprocess all photos
                if args.async_task:
                    # Run as orchestrator Celery task
                    success = scan_and_reprocess_all_async(update_existing=False)
                else:
                    # Run synchronously: scan first, then reprocess
                    print("\n[STEP 1] Scanning known_faces folder...")
                    scan_success = scan_known_faces(update_existing=False)

                    if not scan_success:
                        print("\nScan failed. Aborting reprocessing.")
                        success = False
                    else:
                        print("\n[STEP 2] Reprocessing all gallery photos...")
                        success = reprocess_all_photos()
            else:
                # Just scan
                if args.async_task:
                    success = scan_known_faces_async(update_existing=False)
                else:
                    success = scan_known_faces(update_existing=False)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        success = False
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
