from bson import ObjectId
import re
import os

def time_diff(start, end):
    """Helper function to calculate time difference in seconds."""
    from datetime import datetime
    fmt = "%H:%M:%S,%f"
    start_time = datetime.strptime(start, fmt)
    end_time = datetime.strptime(end, fmt)
    return (end_time - start_time).total_seconds()

import re
from datetime import datetime, timedelta

def time_diff(start, end):
    """Calculate the difference in seconds between two SRT timestamps."""
    fmt = "%H:%M:%S,%f"
    t1 = datetime.strptime(start, fmt)
    t2 = datetime.strptime(end, fmt)
    return (t2 - t1).total_seconds()


def restructure_srt(input_srt_path, max_words=10, max_duration=3):
    """
    Converts word-by-word SRT subtitles into structured blocks and overwrites the existing file.

    - max_words: Maximum words per subtitle block.
    - max_duration: Maximum time (seconds) per subtitle block.
    """
    with open(input_srt_path, "r", encoding="utf-8") as file:
        content = file.readlines()

    subtitle_entries = []
    buffer = []
    start_time = None
    last_time = None

    time_pattern = re.compile(r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})")

    for line in content:
        line = line.strip()
        
        if line.isdigit():  # Skip subtitle index numbers
            continue
        
        if "-->" in line:  # Timestamp line
            match = time_pattern.search(line)
            if match:
                start, end = match.groups()
                if not start_time:
                    start_time = start
                last_time = end
        elif line:  # Subtitle text
            buffer.append(line)

        if len(buffer) >= max_words or (start_time and last_time and time_diff(start_time, last_time) >= max_duration):
            subtitle_entries.append((start_time, last_time, " ".join(buffer)))
            buffer = []
            start_time = None

    # Ensure the last subtitle block is added
    if buffer and start_time and last_time:
        subtitle_entries.append((start_time, last_time, " ".join(buffer)))

    # Overwrite the existing SRT file with the restructured subtitles
    with open(input_srt_path, "w", encoding="utf-8") as output_file:
        for idx, (start, end, text) in enumerate(subtitle_entries, 1):
            output_file.write(f"{idx}\n{start} --> {end}\n{text}\n\n")



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



tgt_langs = {
    "hindi": "hin_Deva",
    "urdu": "urd_Arab",
    "gujrati": "guj_Gujr",
    "marathi": "mar_Deva",
    "telugu": "tel_Telu",
    "kannada": "kan_Knda",
    "malayalam": "mal_Mlym",
    "tamil": "tam_Taml",
    "bengali": "ben_Beng",
}

# Your provided LANGUAGES dictionary
LANGUAGES = {
    "english": {
        "voice": "en-IN-NeerjaNeural",
        "rate": "+5%",
        "pitch": "-5Hz",
        "generate_subtitles": True
    },
    "hindi": {
        "voice": "hi-IN-SwaraNeural",
        "rate": "+5%",
        "pitch": "-5Hz",
        "generate_subtitles": True
    },
    "urdu": {
        "voice": "ur-PK-UzmaNeural",
        "rate": "+5%",
        "pitch": "-5Hz",
        "generate_subtitles": True
    },
    "gujrati": {
        "voice": "gu-IN-NiranjanNeural",
        "rate": "+5%",
        "pitch": "-5Hz",
        "generate_subtitles": True
    },
    "marathi": {
        "voice": "mr-IN-AarohiNeural",
        "rate": "+5%",
        "pitch": "-5Hz",
        "generate_subtitles": True
    },
    "telugu": {
        "voice": "te-IN-MohanNeural",
        "rate": "+5%",
        "pitch": "-5Hz",
        "generate_subtitles": True
    },
    "kannada": {
        "voice": "kn-IN-GaganNeural",
        "rate": "+5%",
        "pitch": "-5Hz",
        "generate_subtitles": True
    },
    "malayalam": {
        "voice": "ml-IN-MidhunNeural",
        "rate": "+5%",
        "pitch": "-5Hz",
        "generate_subtitles": True
    },
    "tamil": {
        "voice": "ta-IN-PallaviNeural",
        "rate": "+5%",
        "pitch": "-5Hz",
        "generate_subtitles": True
    },
    "bengali": {
        "voice": "bn-IN-TanishaaNeural",
        "rate": "+5%",
        "pitch": "-5Hz",
        "generate_subtitles": True
    },
}

rootFolder = os.path.dirname(os.path.abspath(__file__))

from datetime import datetime

def parse_date_posted(date_posted_str):
    # Example input: "Posted On: 24 AUG 2024 9:48AM by PIB Delhi"
    date_pattern = r"Posted On: (\d{2}) (\w{3}) (\d{4}) (\d{1,2}):(\d{2})(AM|PM)"
    import re
    match = re.match(date_pattern, date_posted_str)

    # If the input string doesn't match the pattern, return None or raise an error
    if not match:
        print(f"Invalid date format: {date_posted_str}")
        return None  # or raise ValueError("Invalid date format")

    # Extract components
    day, month, year, hour, minute, period = match.groups()

    # Convert month abbreviation to number
    month_map = {
        "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
        "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12
    }
    month_number = month_map[month.upper()]  # Ensure month is uppercase

    # Convert 12-hour format to 24-hour format
    hour = int(hour)
    if period == "PM" and hour < 12:
        hour += 12
    if period == "AM" and hour == 12:
        hour = 0

    # Create and return the datetime object
    return datetime(
        year=int(year),
        month=month_number,
        day=int(day),
        hour=hour,
        minute=int(minute)
    )

# Example usage
date_str = "Posted On: 24 AUG 2024 9:48AM by PIB Delhi"
parsed_date = parse_date_posted(date_str)
print(parsed_date)  # Output: 2024-08-24 09:48:00