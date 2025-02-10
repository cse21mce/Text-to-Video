
import os
import openai
import json
import base64
import requests
from dotenv import load_dotenv
from googleapiclient.discovery import build
from typing import List, Dict
from logger import log_info, log_warning, log_error, log_success

load_dotenv()

# Configure APIs
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID")
openai.api_key = os.getenv("OPENAI_API_KEY")
IMAGE_GEN_URL = os.getenv("IMAGE_GEN_URL")
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
    Analyze the given text and extract 10-12 most important visual concepts or scenes that could be searched for images. 
    If the content mentions any name of Person, Organisation, Public Figure, or State, try to incorporate it as well.
    Each concept should be a clear, concise phrase that would work well for image search and AI image generation.
    Return only the list of phrases in a JSON array format, nothing else.
    Example output: ["traditional Indian handicrafts on display", "Ministry of Statistics and Programme Implementation", "solar panel installation"]
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


def generate_image_prompt(summary: str, chunk: str) -> str:
    """
    Generate a suitable AI image generation prompt using GPT.

    Args:
        summary (str): The full summary of the content.
        chunk (str): A specific extracted visual concept.

    Returns:
        str: Generated prompt for AI image generation.
    """
    system_prompt = """
    You are an expert in generating visual imagery prompts. Given a summary and a specific concept, 
    generate a concise and detailed prompt suitable for AI image generation.
    
    Ensure:
    - The prompt is visually descriptive yet concise.
    - It maintains coherence with the summary.
    - It does not exceed 30 words.

    Example:
    Summary: "The Indian government launched a solar energy initiative for rural areas."
    Concept: "solar panel installation"
    Output: "A high-quality image of a solar panel installation in a rural Indian village, bright sunlight, and workers installing solar panels."
    """

    completion = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Summary: {summary}\nConcept: {chunk}"}
        ],
        max_tokens=50,
        temperature=0.5
    )

    return completion.choices[0].message.content.strip()


def generate_image(prompt: str, width: int = 720, height: int = 1280) -> str:
    """
    Generate an image using AI and return the base64-decoded image.

    Args:
        prompt (str): AI-generated image prompt.
        width (int): Image width.
        height (int): Image height.

    Returns:
        str: Path to the saved image.
    """
    payload = {
        "prompt": prompt,
        "width": width,
        "height": height,
        "guidance_scale": 4,
        "num_inference_steps": 10,
        "max_sequence_length": 512,
        "seed": 48029153120338
    }

    response = requests.post(IMAGE_GEN_URL, json=payload)

    if response.status_code == 200:
        image_data = response.json().get("image", "")
        if image_data:
            image_bytes = base64.b64decode(image_data)
            image_path = f"output/generated_images/{prompt[:20].replace(' ', '_')}.png"
            os.makedirs("output/generated_images", exist_ok=True)
            with open(image_path, "wb") as img_file:
                img_file.write(image_bytes)
            return image_path
    return None


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

    search_query = f"site:{PIB_SITE} {prompt}" if prioritize_pib else f"-site:{PIB_SITE} {prompt}"

    res = service.cse().list(
        q=search_query,
        cx=SEARCH_ENGINE_ID,
        searchType='image',
        num=num_images
    ).execute()

    return [{
        'url': item['link'],
        'source': item.get('displayLink', ''),
        'title': item.get('title', ''),
        'context': prompt
    } for item in res.get('items', [])]


def search_images_from_content(content: str, num_images_per_chunk: int = 1, max_chunks: int = 8) -> List[Dict]:
    """
    Process content and search for images using both Google Search and AI-generated images.

    Args:
        content (str): Input text to process.
        num_images_per_chunk (int): Images per concept.
        max_chunks (int): Max number of concepts.

    Returns:
        List[Dict]: List of dictionaries containing web and AI-generated images.
    """
    log_info('Generating Images for the post')
    chunks = process_with_gpt(content)
    chunks = chunks[:max_chunks]

    images = []
    for chunk in chunks:
        log_info(f"Generating prompt for image creation for: {chunk}")
        prompt = generate_image_prompt(content, chunk)

        # Web-based image search
        log_info(f"Searching images on web for: {chunk}")
        web_images = google_image_search(chunk, num_images_per_chunk)


        # AI-generated image
        log_info(f"Generating images for: {chunk}")
        ai_image_path = generate_image(prompt)
        filtered_web_image = [img["url"] for img in web_images if not img["url"].startswith("https://lookaside")]

        images.append({
            "concept": chunk,
            "web_image": filtered_web_image[0],
            "ai_generated_image": ai_image_path
        })

    log_success(f"Images generated for the post")
    filtered_data = [{"web_image": item["web_image"], "ai_generated_image": item["ai_generated_image"]} for item in images]

    return filtered_data


# if __name__ == "__main__":
#     content = """
#     Lamp lighting ceremony for 29 Nursing Cadets at College of Nursing, Army Hospital in Delhi featured speeches by senior officers, including Lt Gen Shankar Narayan and Maj Gen Sheena PD. The event emphasized upholding professional standards, passing on knowledge, and the importance of nursing as a calling to serve and make a difference.
#     """

#     images = search_images_from_content(content)
#     print(json.dumps(images, indent=2))










# import os
# import openai
# import json
# from dotenv import load_dotenv
# from googleapiclient.discovery import build
# from typing import List, Dict

# load_dotenv()

# # Configure APIs
# GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
# SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID")
# openai.api_key = os.getenv("OPENAI_API_KEY")
# PIB_SITE = "pib.gov.in"

# def process_with_gpt(content: str) -> List[str]:
#     """
#     Extract visual concepts from content using GPT-3.5.

#     Args:
#         content (str): Input text to process.

#     Returns:
#         List[str]: Extracted visual concepts.
#     """
#     system_prompt = """
#     Analyze the given text and extract 10-12 most important visual concepts or scenes that could be searched for images. If the content mention any name of Person, Organisation, Public Figure or State try to incorporate it as well. 
#     Each concept should be a clear, concise phrase that would work well for image search.
#     Return only the list of phrases in a JSON array format, nothing else.
#     Example output: ["traditional Indian handicrafts on display", "Ministry of Statistics and Programme Implementation", "farmers harvesting wheat crop", "solar panel installation", "Ms. Puja Singh Mandol Additional Secretary", "Attended by representatives from the State Government of Haryana"]
#     """

#     completion = openai.chat.completions.create(
#         model="gpt-3.5-turbo",
#         messages=[
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": content}
#         ],
#         max_tokens=150,
#         temperature=0.3
#     )

#     response_text = completion.choices[0].message.content.strip()

#     try:
#         chunks = json.loads(response_text)
#         return chunks if isinstance(chunks, list) else [response_text]
#     except json.JSONDecodeError:
#         return [phrase.strip() for phrase in response_text.split('\n') if phrase.strip()]


# def google_image_search(prompt: str, num_images: int = 1, prioritize_pib: bool = False) -> List[Dict]:
#     """
#     Search images using Google Custom Search API.

#     Args:
#         prompt (str): Search query.
#         num_images (int): Number of images to return.
#         prioritize_pib (bool): Prioritize PIB site in search.

#     Returns:
#         List[Dict]: Image search results.
#     """
#     service = build("customsearch", "v1", developerKey=GOOGLE_API_KEY)

#     search_query = f"site:{PIB_SITE} {prompt}" if prioritize_pib else f"-site:{PIB_SITE} {prompt}"

#     res = service.cse().list(
#         q=search_query,
#         cx=SEARCH_ENGINE_ID,
#         searchType='image',
#         num=num_images
#     ).execute()

#     image_results = [{
#         'url': item['link'],
#         'source': item.get('displayLink', ''),
#         'title': item.get('title', ''),
#         'context': prompt
#     } for item in res.get('items', [])]

#     if prioritize_pib and not image_results:
#         return google_image_search(prompt, num_images, False)
        
#     return image_results


# def search_images_from_content(content: str, num_images_per_chunk: int = 1, max_chunks: int = 8) -> List[Dict]:
#     """
#     Process content and search for related images.

#     Args:
#         content (str): Input text to process.
#         num_images_per_chunk (int): Images per concept.
#         max_chunks (int): Max number of concepts.

#     Returns:
#         List[Dict]: Image search results.
#     """
#     chunks = process_with_gpt(content)
#     chunks = chunks[:max_chunks]

#     images = []
#     for chunk in chunks:
#         chunk_results = google_image_search(chunk, num_images_per_chunk)
#         images.extend(chunk_results)

#     return images



