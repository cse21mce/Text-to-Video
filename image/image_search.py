import os
import openai
import json
from dotenv import load_dotenv
from googleapiclient.discovery import build
from typing import List, Dict

load_dotenv()

# Configure APIs
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID")
openai.api_key = os.getenv("OPENAI_API_KEY")
PIB_SITE = "pib.gov.in"

def process_with_gpt(content: str) -> List[str]:
    """
    Extract visual concepts from content using GPT-3.5.

    Args:
        content (str): Input text to process.

    Returns:
        List[str]: Extracted visual concepts.
    """
    system_prompt = """
    Analyze the given text and extract 10-12 most important visual concepts or scenes that could be searched for images. If the content mention any name of Person, Organisation, Public Figure or State try to incorporate it as well. 
    Each concept should be a clear, concise phrase that would work well for image search.
    Return only the list of phrases in a JSON array format, nothing else.
    Example output: ["traditional Indian handicrafts on display", "Ministry of Statistics and Programme Implementation", "farmers harvesting wheat crop", "solar panel installation", "Ms. Puja Singh Mandol Additional Secretary", "Attended by representatives from the State Government of Haryana"]
    """

    completion = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content}
        ],
        max_tokens=150,
        temperature=0.3
    )

    response_text = completion.choices[0].message.content.strip()

    try:
        chunks = json.loads(response_text)
        return chunks if isinstance(chunks, list) else [response_text]
    except json.JSONDecodeError:
        return [phrase.strip() for phrase in response_text.split('\n') if phrase.strip()]


def google_image_search(prompt: str, num_images: int = 1, prioritize_pib: bool = False) -> List[Dict]:
    """
    Search images using Google Custom Search API.

    Args:
        prompt (str): Search query.
        num_images (int): Number of images to return.
        prioritize_pib (bool): Prioritize PIB site in search.

    Returns:
        List[Dict]: Image search results.
    """
    service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)

    search_query = f"site:{PIB_SITE} {prompt}" if prioritize_pib else prompt

    res = service.cse().list(
        q=search_query,
        cx=SEARCH_ENGINE_ID,
        searchType='image',
        num=num_images
    ).execute()

    image_results = [{
        'url': item['link'],
        'source': item.get('displayLink', ''),
        'title': item.get('title', ''),
        'context': prompt
    } for item in res.get('items', [])]

    if prioritize_pib and not image_results:
        return google_image_search(prompt, num_images, False)
        
    return image_results


def search_images_from_content(content: str, num_images_per_chunk: int = 1, max_chunks: int = 8) -> List[Dict]:
    """
    Process content and search for related images.

    Args:
        content (str): Input text to process.
        num_images_per_chunk (int): Images per concept.
        max_chunks (int): Max number of concepts.

    Returns:
        List[Dict]: Image search results.
    """
    chunks = process_with_gpt(content)
    chunks = chunks[:max_chunks]

    images = []
    for chunk in chunks:
        chunk_results = google_image_search(chunk, num_images_per_chunk)
        images.extend(chunk_results)

    return images