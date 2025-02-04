import pymongo
import os
from dotenv import load_dotenv
from bson import ObjectId
from logger import log_info, log_warning, log_error, log_success

load_dotenv()

def connect_to_db():
    """
    Connect to MongoDB database.

    Returns:
        pymongo.collection.Collection: MongoDB collection object.
    """
    try:
        client = pymongo.MongoClient(os.getenv("MONGO_URI"))
        db = client['pib']
        log_success("Connected to database.")
        return db['press_releases']
    except pymongo.errors.ConnectionError as e:
        log_error(f"Database connection failed: {e}")
        return None

def is_url_scraped(url):
    """
    Check if URL is already scraped and stored.

    Args:
        url (str): URL to check.

    Returns:
        dict: Document if URL exists, None otherwise.
    """
    try:
        collection = connect_to_db()
        result = collection.find_one({'url': url})
        log_info(f"URL {'already' if result else 'not'} scraped: {url}")
        return result
    except Exception as e:
        log_error(f"Error checking URL: {e}")
        raise

def store_scraped_data_in_db(data):
    """
    Store scraped data in MongoDB.

    Args:
        data (dict or list): Data to store.

    Returns:
        dict or list: Inserted/updated document(s).
    """
    try:
        collection = connect_to_db()
        if isinstance(data, dict):
            result = collection.update_one({'url': data['url']}, {'$set': data}, upsert=True)
            updated_doc = collection.find_one({'url': data['url']})
            log_info(f"{'Inserted' if result.upserted_id else 'Updated'} document: {data['url']}")
            return updated_doc
        elif isinstance(data, list):
            updated_docs = []
            for item in data:
                collection.update_one({'url': item['url']}, {'$set': item}, upsert=True)
                updated_docs.append(collection.find_one({'url': item['url']}))
            log_info(f"Inserted/Updated {len(data)} documents.")
            return updated_docs
        else:
            raise ValueError("Data must be dict or list of dicts.")
    except Exception as e:
        log_error(f"Error storing data: {e}")
        raise

def update_translation_status(_id, language, status):
    """
    Update translation status.

    Args:
        _id (ObjectId): Document ID.
        language (str): Translation language.
        status (str): New status.
    """
    collection = connect_to_db()
    result = collection.update_one(
        {"_id": ObjectId(_id)},
        {"$set": {f"translations.{language}.status": status}}
    )
    if result.matched_count > 0:
        log_info(f"Translation in '{language}' is '{status}'.")

def store_translation_in_db(_id, language, translation_data):
    """
    Store translation in database.

    Args:
        _id (ObjectId): Document ID.
        language (str): Translation language.
        translation_data (dict): Translation data.
    """
    collection = connect_to_db()
    result = collection.update_one(
        {"_id": ObjectId(_id)},
        {"$set": {f"translations.{language}": translation_data}},
        upsert=True
    )
    if result.matched_count > 0:
        log_success(f"Translation in '{language}' completed.")

def check_translation_in_db(_id, lang):
    """
    Check if translation exists.

    Args:
        _id (ObjectId): Document ID.
        lang (str): Language to check.

    Returns:
        dict: Translation data if exists and completed, None otherwise.
    """
    collection = connect_to_db()
    result = collection.find_one({"_id": ObjectId(_id), f"translations.{lang}": {"$exists": True}})
    if result and result.get("translations").get(lang).get("status") == "completed":
        log_info(f"Translation for '{lang}' exists.")
        return result["translations"].get(lang)
    log_warning(f"Translation for '{lang}' does not exist.")
    return None

def release_exist_with_title(title):
    """
    Check if press release with title exists.

    Args:
        title (str): Title to check.

    Returns:
        dict: Document if exists, None otherwise.
    """
    collection = connect_to_db()
    document = collection.find_one({"title": title})
    log_info(f"Document with title '{title}' {'exists' if document else 'not found'}.")
    return document