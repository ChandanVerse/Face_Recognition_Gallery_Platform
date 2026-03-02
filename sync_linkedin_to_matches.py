"""
Script to sync LinkedIn profiles from known_people to tagged_people array in photos collection.
This updates all tagged people records with the current LinkedIn profile URLs.
Uses parallel processing and bulk operations for maximum performance.
"""

import os
import sys
import logging
import time
from pymongo import MongoClient
from pymongo.operations import UpdateOne
from bson import ObjectId
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Number of parallel threads
NUM_THREADS = 8
# Batch size for bulk operations
BATCH_SIZE = 100


def process_batch(client, db_name, batch_photos):
    """Process a batch of photos in a separate thread."""
    db = client[db_name]
    known_people_col = db['known_people']
    photos_col = db['photos']

    # Build a map of person_id to linkedin_profile
    known_people_map = {}
    for person in known_people_col.find({}):
        known_people_map[str(person["_id"])] = person.get('linkedin_profile')

    update_operations = []
    modified_count = 0

    for photo in batch_photos:
        tagged_people = photo.get('tagged_people', [])
        if not tagged_people:
            continue

        updates_needed = []
        for idx, tagged in enumerate(tagged_people):
            person_id = str(tagged.get('person_id'))
            if person_id in known_people_map:
                new_linkedin = known_people_map[person_id]
                current_linkedin = tagged.get('linkedin_profile')
                if new_linkedin != current_linkedin:
                    updates_needed.append((idx, new_linkedin))

        # Apply updates for this photo
        if updates_needed:
            for idx, linkedin in updates_needed:
                update_operations.append(
                    UpdateOne(
                        {"_id": photo["_id"]},
                        {"$set": {f"tagged_people.{idx}.linkedin_profile": linkedin}}
                    )
                )
            modified_count += 1

    # Bulk write operations
    if update_operations:
        result = photos_col.bulk_write(update_operations)
        return modified_count
    return 0


def main():
    """Main function to sync LinkedIn profiles with parallel processing."""

    # Get MongoDB configuration
    mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
    db_name = os.getenv('MONGODB_DB_NAME', 'face_recognition_db')

    logger.info("\n" + "="*60)
    logger.info("Syncing LinkedIn Profiles to Matches (Parallel)")
    logger.info("="*60)
    logger.info(f"Parallel threads: {NUM_THREADS}")
    logger.info(f"Batch size: {BATCH_SIZE}")
    logger.info(f"MongoDB: {db_name}")
    logger.info("="*60 + "\n")

    start_time = time.time()

    try:
        # Connect to MongoDB
        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        db = client[db_name]
        photos_col = db['photos']

        # Test connection
        db.command('ping')
        logger.info("Connected to MongoDB successfully\n")

        # Get all photos with tagged people
        total_photos = photos_col.count_documents({'tagged_people': {'$exists': True, '$ne': []}})
        logger.info(f"Total photos with tagged people: {total_photos}\n")

        if total_photos == 0:
            logger.warning("No photos with tagged people found to process!")
            client.close()
            return

        # Fetch all photos with tagged people
        logger.info("Fetching photos from database...")
        all_photos = list(photos_col.find({'tagged_people': {'$exists': True, '$ne': []}}))
        logger.info(f"Fetched {len(all_photos)} photos\n")

        # Split into batches
        batches = [all_photos[i:i + BATCH_SIZE] for i in range(0, len(all_photos), BATCH_SIZE)]
        logger.info(f"Processing {len(batches)} batches with {NUM_THREADS} parallel threads...\n")

        # Process batches in parallel
        total_updated = 0
        with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
            futures = []
            for batch_idx, batch in enumerate(batches):
                future = executor.submit(process_batch, client, db_name, batch)
                futures.append((batch_idx, future))

            # Track progress
            completed = 0
            for batch_idx, future in futures:
                try:
                    updated = future.result()
                    total_updated += updated
                    completed += 1

                    if completed % 10 == 0:
                        logger.info(f"Progress: {completed}/{len(batches)} batches completed")

                except Exception as e:
                    logger.error(f"Error processing batch {batch_idx}: {e}")

        # Print summary
        elapsed_time = time.time() - start_time
        logger.info("\n" + "="*60)
        logger.info("SYNC SUMMARY")
        logger.info("="*60)
        logger.info(f"Total photos processed: {total_photos}")
        logger.info(f"Photos updated: {total_updated}")
        logger.info(f"Time taken: {elapsed_time:.2f} seconds")
        logger.info(f"Speed: {total_photos / elapsed_time:.0f} photos/second")
        logger.info("="*60 + "\n")

        # Verify results
        logger.info("Verifying sync...\n")

        photos_with_linkedin = photos_col.count_documents(
            {"tagged_people.linkedin_profile": {"$ne": None}}
        )

        logger.info(f"Photos with LinkedIn profiles in tagged_people: {photos_with_linkedin}")

        # Show sample of updated records
        logger.info("\nSample of updated records:")
        logger.info("-" * 60)
        sample_photos = photos_col.find(
            {"tagged_people.linkedin_profile": {"$ne": None}},
            {"tagged_people": 1, "_id": 0}
        ).limit(3)

        for photo in sample_photos:
            for tagged in photo.get('tagged_people', []):
                if tagged.get('linkedin_profile'):
                    logger.info(f"  {tagged['person_name']}: {tagged['linkedin_profile']}")

        logger.info("-" * 60 + "\n")

        if total_updated > 0:
            logger.info("SUCCESS: LinkedIn profiles synced successfully!")
        else:
            logger.warning("WARNING: No matches were updated. Check the data.")

        client.close()
        logger.info("Disconnected from MongoDB\n")

    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
