#!/usr/bin/env python3
"""
Check MongoDB database collections and document structure
"""

import sys
from backend.config.database import get_database

def check_database():
    """Check all collections and their document count"""
    print("\n" + "="*80)
    print("MONGODB DATABASE CHECK")
    print("="*80)

    try:
        db = get_database()

        # Get all collections
        collections = db.list_collection_names()

        print(f"\n[OK] Connected to MongoDB")
        print(f"Total collections: {len(collections)}\n")

        collection_info = {}

        # Check each collection
        for collection_name in sorted(collections):
            try:
                count = db[collection_name].count_documents({})
                collection_info[collection_name] = count

                print(f"{'Collection':<30} {'Count':<10} {'Sample'}")
                print(f"{collection_name:<30} {count:<10}", end="")

                if count > 0:
                    sample = db[collection_name].find_one()
                    keys = list(sample.keys())[:3]
                    print(f"{', '.join(keys)}")
                else:
                    print("(empty)")

            except Exception as e:
                print(f"{collection_name:<30} ERROR: {e}")

        # Detailed check for important collections
        print("\n" + "="*80)
        print("DETAILED COLLECTION ANALYSIS")
        print("="*80)

        # Photos collection
        if 'photos' in collections:
            print("\n[PHOTOS] Collection:")
            count = db['photos'].count_documents({})
            count_with_faces = db['photos'].count_documents({'face_count': {'$gt': 0}})
            print(f"   Total photos: {count}")
            print(f"   Photos with faces: {count_with_faces}")

            if count > 0:
                sample = db['photos'].find_one()
                print(f"   Sample fields: {list(sample.keys())}")

        # Check embedded faces in photos
        if 'photos' in collections and count > 0:
            print("\n[EMBEDDED FACES] In Photos Collection:")
            photos_with_faces = list(db['photos'].find({'face_count': {'$gt': 0}}).limit(1))
            if photos_with_faces:
                sample_photo = photos_with_faces[0]
                faces = sample_photo.get('faces', [])
                print(f"   Sample photo has {len(faces)} embedded faces")
                if faces:
                    print(f"   Face fields: {list(faces[0].keys())}")
                    print(f"   Note: Embeddings stored in Pinecone, not MongoDB")

        # Known people collection
        if 'known_people' in collections:
            print("\n[KNOWN_PEOPLE] Collection:")
            count = db['known_people'].count_documents({})
            print(f"   Total known people: {count}")

            if count > 0:
                sample = db['known_people'].find_one()
                print(f"   Sample fields: {list(sample.keys())}")

                if 'average_embedding' in sample and sample['average_embedding']:
                    print(f"   Embedding length: {len(sample['average_embedding'])}")

        # Check embedded matched_users in photos
        if 'photos' in collections:
            print("\n[MATCHED_USERS] In Photos Collection:")
            photos_with_matches = db['photos'].count_documents({'matched_users': {'$exists': True, '$ne': []}})
            print(f"   Photos with user matches: {photos_with_matches}")

            if photos_with_matches > 0:
                sample = db['photos'].find_one({'matched_users': {'$exists': True, '$ne': []}})
                if sample:
                    matched_users = sample.get('matched_users', [])
                    print(f"   Sample has {len(matched_users)} matched users")

        # Check embedded tagged_people in photos
        if 'photos' in collections:
            print("\n[TAGGED_PEOPLE] In Photos Collection:")
            photos_with_tags = db['photos'].count_documents({'tagged_people': {'$exists': True, '$ne': []}})
            print(f"   Photos with tagged people: {photos_with_tags}")

            if photos_with_tags > 0:
                sample = db['photos'].find_one({'tagged_people': {'$exists': True, '$ne': []}})
                if sample:
                    tagged_people = sample.get('tagged_people', [])
                    print(f"   Sample has {len(tagged_people)} tagged people")

        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)

        # Check readiness
        print("\n[OK] Database Connection: OK")

        issues = []

        if 'photos' in collections:
            count_with_faces = db['photos'].count_documents({'face_count': {'$gt': 0}})
            if count_with_faces > 0:
                print(f"[OK] Photos with embedded faces: {count_with_faces}")
                print(f"[OK] Note: Embeddings stored in Pinecone (not MongoDB)")
            else:
                print("[WARNING] No photos with detected faces (upload photos first)")

        if 'known_people' in collections:
            count = db['known_people'].count_documents({})
            if count > 0:
                print(f"[OK] Known people indexed: {count}")
            else:
                print("[WARNING] No known people (run: python3 scan_known_faces.py --scan)")

        if 'users' in collections:
            users_with_profiles = db['users'].count_documents({'avg_embedding': {'$exists': True, '$ne': None}})
            if users_with_profiles > 0:
                print(f"[OK] Users with profiles created: {users_with_profiles}")

        if issues:
            print("\n[WARNING] Issues Found:")
            for issue in issues:
                print(f"  {issue}")

        print(f"\n[OK] System is {'READY' if not issues or len(issues) == 1 else 'NEEDS SETUP'}")
        print("="*80 + "\n")

    except Exception as e:
        print(f"[ERROR] Database Connection Error: {e}")
        print("Make sure MongoDB is running and DATABASE_URL is configured in .env")
        return False

    return True

if __name__ == "__main__":
    success = check_database()
    sys.exit(0 if success else 1)
