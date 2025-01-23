from bson import ObjectId
import re


def rename(title: str) -> str:
    """
    Converts a given title into a folder-name-friendly format.
    
    Args:
        title (str): The input title.
    
    Returns:
        str: A folder-name-friendly version of the title.
    """
    # Remove special characters, except spaces, hyphens, and underscores
    sanitized = re.sub(r'[^\w\s\-]', '', title)
    
    # Replace spaces with underscores
    sanitized = sanitized.replace(' ', '_')
    
    # Trim any leading or trailing underscores
    sanitized = sanitized.strip('_')
    
    # Ensure the length is reasonable for file systems
    max_length = 245  # Max length for most file systems
    return sanitized[:max_length]


def convert_object_ids(data):
    """
    Converts ObjectId instances to strings for JSON serialization.
    """
    if isinstance(data, dict):
        return {k: convert_object_ids(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_object_ids(item) for item in data]
    elif isinstance(data, ObjectId):
        return str(data)
    else:
        return data