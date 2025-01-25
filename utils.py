from bson import ObjectId
import re

def rename(title: str) -> str:
    """
    Convert title to folder-name-friendly format.

    Args:
        title (str): Input title.

    Returns:
        str: Folder-name-friendly version of title.
    """
    sanitized = re.sub(r'[^\w\s\-]', '', title)
    sanitized = sanitized.replace(' ', '_').strip('_')
    return sanitized[:245]

def convert_object_ids(data):
    """
    Convert ObjectId instances to strings for JSON serialization.

    Args:
        data (Any): Input data which has mongodb ObjectId to convert into string.

    Returns:
        Any: Data with ObjectIds converted to strings.
    """
    if isinstance(data, dict):
        return {k: convert_object_ids(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_object_ids(item) for item in data]
    elif isinstance(data, ObjectId):
        return str(data)
    return data

def split_sentences(text):
    """
    Split text into sentences while preserving common abbreviations.

    Args:
        text (str): Input text to split.

    Returns:
        list: List of sentences.
    """
    sentence_pattern = r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s'
    return [s.strip() for s in re.split(sentence_pattern, text) if s.strip()]

def save_html_to_file(soup):
    """
    Save BeautifulSoup HTML content to a file.

    Args:
        soup (BeautifulSoup): Parsed HTML content.

    Returns:
        str: Path to the saved file.
    """
    import os
    os.makedirs('html_outputs', exist_ok=True)
    filepath = os.path.join('html_outputs', 'index.html')
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(str(soup.prettify()))
    print(f"HTML content saved to {filepath}")
    return filepath