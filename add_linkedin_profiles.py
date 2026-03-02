"""
Script to add LinkedIn profile URLs to known people in the database.
"""

import os
import sys
import logging
from pymongo import MongoClient
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# LinkedIn profiles to add
LINKEDIN_PROFILES = {
    "Abhishek Sukhwal": "https://www.linkedin.com/in/abhisheksukhwal/",
    "Manish Gupta": "https://www.linkedin.com/in/manishgupta05/",
    "Peter Marrs": "https://www.linkedin.com/in/peter-marrs-3516b81/",
    "Vinayak Muzumdar": "https://www.linkedin.com/in/vinayakmuzumdar",
    "Mandira Bedi": "https://www.linkedin.com/in/mandira-bedi-2a081b26a/",
    "Mridu Bhandari": "https://www.linkedin.com/in/mridu-bhandari-publicspeaking-coach/",
    "Shankar Subramanian": "https://www.linkedin.com/in/subramanianshankar/overlay/about-this-profile/",
    "Sriram Sridharan": "https://www.linkedin.com/in/sriram-sridharan-443774363/overlay/about-this-profile/",
    "Venkat Sitaram": "https://www.linkedin.com/in/venkat-sitaram-8798a8b0/overlay/about-this-profile/"
}


def main():
    """Main function to add LinkedIn profiles."""

    # Get MongoDB configuration
    mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
    db_name = os.getenv('MONGODB_DB_NAME', 'face_recognition_db')

    logger.info("\n" + "="*60)
    logger.info("Adding LinkedIn Profiles to Known People")
    logger.info("="*60)
    logger.info(f"MongoDB URI: {mongodb_uri}")
    logger.info(f"Database: {db_name}")
    logger.info(f"People to update: {len(LINKEDIN_PROFILES)}")
    logger.info("="*60 + "\n")

    try:
        # Connect to MongoDB
        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        db = client[db_name]
        collection = db['known_people']

        # Test connection
        db.command('ping')
        logger.info("✅ Connected to MongoDB successfully\n")

        # Update each person with their LinkedIn profile
        updated_count = 0
        not_found_count = 0

        for name, linkedin_url in LINKEDIN_PROFILES.items():
            logger.info(f"Updating: {name}")
            logger.info(f"  LinkedIn: {linkedin_url}")

            result = collection.update_one(
                {"name": name},
                {"$set": {"linkedin_profile": linkedin_url}}
            )

            if result.matched_count > 0:
                logger.info(f"  ✅ Updated successfully\n")
                updated_count += 1
            else:
                logger.warning(f"  ⚠️  Person not found in database\n")
                not_found_count += 1

        # Print summary
        logger.info("="*60)
        logger.info("SUMMARY")
        logger.info("="*60)
        logger.info(f"Total to update: {len(LINKEDIN_PROFILES)}")
        logger.info(f"Successfully updated: {updated_count}")
        logger.info(f"Not found: {not_found_count}")
        logger.info("="*60 + "\n")

        if updated_count == len(LINKEDIN_PROFILES):
            logger.info("✅ All LinkedIn profiles added successfully!")
        else:
            logger.warning(f"⚠️  {not_found_count} people not found in database")

        client.close()
        logger.info("✅ Disconnected from MongoDB\n")

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
