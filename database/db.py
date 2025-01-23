import pymongo
import os
import logging
from dotenv import load_dotenv
from bson import ObjectId

# Load environment variables from .env file
load_dotenv()

# Importing custom logger
from logger import log_info, log_warning, log_error,log_success

# Set up logging
logger = logging.getLogger(__name__)

def connect_to_db():
    """
    Connects to the MongoDB database.
    
    Returns:
    - collection: The MongoDB collection object.
    """
    try:
        MONGO_URI = os.getenv("MONGO_URI")
        client = pymongo.MongoClient(MONGO_URI)
        db = client['pib']
        log_success("Successfully connected to the database.")
        return db['press_releases']
    except pymongo.errors.ConnectionError as e:
        log_error(f"Database connection failed: {e}")
        return None

def is_url_scraped(url):
    """
    Checks if a URL has already been scraped and stored in the MongoDB collection.

    Args:
        url (str): The URL to check.

    Returns:
        dict: Object if the URL exists in the database, None otherwise.
    """
    try:
        collection = connect_to_db()
        result = collection.find_one({'url': url})
        if result:
            log_info(f"URL already scraped: {url}")
            return result
        else:
            log_info(f"URL not found in the database: {url}")
            return None
    except Exception as e:
        log_error(f"Error checking URL in MongoDB: {e}")
        raise e

def store_scraped_data_in_db(data):
    """
    Stores the scraped data into MongoDB.
    If a document with the same URL exists, it updates it; otherwise, inserts a new document.
    Returns the inserted/updated document(s) including the `_id` field.
    """
    try:
        collection = connect_to_db()
        if isinstance(data, dict):
            result = collection.update_one(
                {'url': data['url']},
                {'$set': data},
                upsert=True
            )
            # Fetch and return the document
            updated_doc = collection.find_one({'url': data['url']})
            if result.upserted_id:
                log_info(f"Inserted new document with URL: {data['url']}")
            else:
                log_info(f"Updated existing document with URL: {data['url']}")
            return updated_doc

        elif isinstance(data, list):
            updated_docs = []
            for item in data:
                collection.update_one(
                    {'url': item['url']},
                    {'$set': item},
                    upsert=True
                )
                # Fetch and append each updated document
                updated_docs.append(collection.find_one({'url': item['url']}))
            log_info(f"Inserted/Updated {len(data)} documents.")
            return updated_docs

        else:
            log_error("Data must be a dict or list of dicts.")
            raise ValueError("Data must be a dict or list of dicts.")

    except Exception as e:
        log_error(f"Error storing data to MongoDB: {e}")
        raise e

def update_translation_status(_id, language, status):
    """
    Update the status of a specific translation for a press release in the database.
    """
    collection = connect_to_db()

    # Build the filter query to find the document by title
    filter_query = {"_id": ObjectId(_id)}

    # Construct the update query to update the specific translation status
    update_query = {
        "$set": {
            f"translations.{language}.status": status
        }
    }

    # Update the document with the specific translation status
    result = collection.update_one(filter_query, update_query)
    
    if result.matched_count > 0:
        log_info(f"Translation in '{language}' is '{status}'.")

def store_translation_in_db(_id, language, translation_data):
    """
    Store a specific translation for a press release in the database.
    """
    collection = connect_to_db()

    # Build the filter query to find the document by title
    filter_query = {"_id": ObjectId(_id)}

    # Construct the update query to update the specific translation
    update_query = {
        "$set": {
            f"translations.{language}": translation_data,
        }
    }

    # Update the document with the specific translation
    result = collection.update_one(filter_query, update_query, upsert=True)

    if result.matched_count > 0:
        log_success(f"Translation in '{language}' is Completed.")

def check_translation_in_db(_id, lang):
    """
    Check if a specific translation for a press release already exists in the database.
    """
    collection = connect_to_db()

    # Check if the specific translation exists
    translation_query = {"_id": ObjectId(_id), f"translations.{lang}": {"$exists": True}}
    result = collection.find_one(translation_query)

    if result:
        log_info(f"Translation for '{lang}' already exists.")
        return result["translations"].get(lang)
    else:
        log_warning(f"Translation for '{lang}' does not exist.")
        return None

def release_exist_with_title(title):
    """
    Check if a specific title for a press release already exists in the database.
    """
    collection = connect_to_db()

    # First, check if the document with the title exists
    title_exists_query = {"title": title}
    document = collection.find_one(title_exists_query)

    if not document:
        log_warning(f"No document found with title: {title}")
        return None
    else:
        log_info(f"Document with title '{title}' exists.")
        return document
