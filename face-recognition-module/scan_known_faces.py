#!/usr/bin/env python3
"""
CLI tool to scan the known_faces directory and index all known people.

Usage:
    python scan_known_faces.py                    # Scan all people
    python scan_known_faces.py --update           # Update existing people
    python scan_known_faces.py --list             # List all known people
"""

import argparse
import logging
import sys
import os
from pathlib import Path

# Add parent directory to path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

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


def scan_known_faces(update_existing: bool = False):
    """Scan the known_faces directory and index all people."""
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


def delete_person(person_name: str):
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
            print(f"[OK] Successfully deleted '{person_name}'")
        else:
            print(f"[FAILED] Failed to delete '{person_name}'")

        return success

    except Exception as e:
        logger.error(f"Error deleting person: {e}")
        return False
    finally:
        if 'db' in locals():
            db.disconnect()


def update_person_info(person_name: str, role: str = None, metadata: dict = None):
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
            print(f"[OK] Successfully updated '{person_name}'")
        else:
            print(f"[FAILED] Failed to update '{person_name}'")

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
  python scan_known_faces.py                      # Scan all people
  python scan_known_faces.py --update             # Update existing people
  python scan_known_faces.py --list               # List all known people
  python scan_known_faces.py --delete John        # Delete person named 'John'
  python scan_known_faces.py --update-info John --role Manager  # Update role
        """
    )

    parser.add_argument('--scan', action='store_true', help='Scan and index known faces')
    parser.add_argument('--update', action='store_true',
                        help='Scan and update existing people entries')
    parser.add_argument('--list', action='store_true', help='List all known people')
    parser.add_argument('--delete', type=str, metavar='NAME', help='Delete a known person')
    parser.add_argument('--update-info', type=str, metavar='NAME', help='Update person info')
    parser.add_argument('--role', type=str, help='Role/title for person')
    parser.add_argument('--metadata', type=str, help='JSON metadata for person')

    args = parser.parse_args()

    # If no arguments provided, default to scan
    if not any([args.scan, args.update, args.list, args.delete, args.update_info]):
        args.scan = True

    success = True

    try:
        if args.list:
            success = list_known_people()
        elif args.delete:
            success = delete_person(args.delete)
        elif args.update_info:
            metadata = None
            if args.metadata:
                import json
                try:
                    metadata = json.loads(args.metadata)
                except json.JSONDecodeError:
                    print("Invalid JSON in --metadata")
                    return 1
            success = update_person_info(args.update_info, role=args.role, metadata=metadata)
        elif args.update:
            success = scan_known_faces(update_existing=True)
        else:  # args.scan
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
