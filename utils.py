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
    
def split_sentences(text):
    # Regular expression to split sentences while preserving abbreviations
    # This handles common abbreviations like Mr., Mrs., Dr., H.E., etc.
    sentence_pattern = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s'
    sentences = re.split(sentence_pattern, text)
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def save_html_to_file(soup):
    """
    Save the HTML content of a BeautifulSoup object to a file.
    
    Args:
    - soup (BeautifulSoup): Parsed HTML content
    
    Returns:
    - str: Path to the saved file
    """
    import os
    
    # Ensure the directory exists
    os.makedirs('html_outputs', exist_ok=True)
    
    # Full path to the file
    filepath = os.path.join('html_outputs', 'index.html')
    
    # Write the HTML content
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(str(soup.prettify()))
    
    print(f"HTML content saved to {filepath}")
    return filepath