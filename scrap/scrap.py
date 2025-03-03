
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import asyncio

# User defined modules
from utils import convert_object_ids,parse_date_posted,rename
from database.db import store_scraped_data_in_db, is_url_scraped
from summarize.summarize import summarize_text
from speech.tts import generate_tts_audio_and_subtitles
from logger import log_info, log_warning, log_error, log_success 
from image.image_search import search_images_from_content
from image.capture_iframe import capture_iframe
from video.create_video import create_video
# from utils import save_html_to_file


# Initialize a session to maintain the connection across requests
session = requests.Session()

BASE_URL = 'https://pib.gov.in/allRel.aspx'

def txt_cleaner(txt):
    """
    Cleans up text by removing extra whitespace, new lines, and carriage returns.
    
    Args:
    - txt (str): The text to be cleaned.
    
    Returns:
    - str: The cleaned text.
    """
    if txt:
        cleaned_string = txt.strip()
        cleaned_string = re.sub(r'\s+', ' ', cleaned_string)
        return cleaned_string
    return ''

def get_form_data():
    """
    Fetches the necessary form data including __VIEWSTATE and __EVENTVALIDATION.
    
    Returns:
    - dict: A dictionary containing form data.
    """
    response = session.get(BASE_URL)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    form_data = {}
    for input_tag in soup.find_all('input', type='hidden'):
        name = input_tag.get('name')
        value = input_tag.get('value', '')
        if name:
            form_data[name] = value

    return form_data

def get_press_releases(date: datetime, ministry_id: str = '0'):
    """
    Fetches press releases for a specific date and ministry.
    """
    try:
        day = date.day
        month = date.month
        year = date.year

        # Get the initial form data
        form_data = get_form_data()
        if not form_data:
            log_error("Failed to retrieve initial form data.")
            return []

        # Update form data with selected values
        payload = {
            'ctl00$ContentPlaceHolder1$ddlMinistry': ministry_id,
            'ctl00$ContentPlaceHolder1$ddlday': str(day),
            'ctl00$ContentPlaceHolder1$ddlMonth': str(month),
            'ctl00$ContentPlaceHolder1$ddlYear': str(year),
            'ctl00$ContentPlaceHolder1$hydregionid': '3',
            'ctl00$ContentPlaceHolder1$hydLangid': '1',
            '__EVENTTARGET': 'ctl00$ContentPlaceHolder1$ddlMinistry',  # Update based on the dropdown
            '__EVENTARGUMENT': '',
        }

        # Merge with the extracted hidden form data
        payload.update(form_data)

        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        response = session.post(BASE_URL, data=payload, headers=headers)
        response.raise_for_status()

        log_info(f"Request URL: {response.url}")
        log_info(f"Response status code: {response.status_code}")

        soup = BeautifulSoup(response.content, 'html.parser')
        content_area = soup.find('div', class_='content-area')
        if not content_area:
            log_warning(f"No press releases found for {date.strftime('%Y-%m-%d')}")
            return []

        releases = []
        for ul in content_area.find_all('ul'):
            ministry_header = ul.find('h3', class_='font104')
            if ministry_header:
                ministry_name = ministry_header.text.strip()
                for li in ul.find_all('li'):
                    a_tag = li.find('a', href=True)
                    if a_tag:
                        title = a_tag.text.strip()
                        relative_url = a_tag['href']
                        full_url = urljoin(BASE_URL, relative_url)
                        releases.append({
                            'title': title,
                            'url': full_url,
                            'ministry': ministry_name,
                            'date': date.strftime('%Y-%m-%d')
                        })
        log_info(f"Found {len(releases)} releases for {date.strftime('%Y-%m-%d')}")
        return releases

    except Exception as e:
        log_error(f"Error fetching press releases for {date.strftime('%Y-%m-%d')}: {e}")
        return []


async def scrape_press_release(url: str):
    """
    Scrape and process press release from given URL.

    Args:
        url (str): Press release URL

    Returns:
        dict: Processed press release data
    """
    try:
        cached_data = is_url_scraped(url)
        if cached_data:
            log_info(f"Retrieved cached data: {url}")
            return convert_object_ids(cached_data)

        log_info(f"Starting fresh scrape: {url}")

        session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.5)
        session.mount('https://', HTTPAdapter(max_retries=retries))

        response = await asyncio.to_thread(
            session.get, 
            url, 
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        content = txt_cleaner(' '.join([p.get_text() for p in soup.select('.innner-page-main-about-us-content-right-part p')]))
        title = txt_cleaner(soup.select_one('div h2').get_text() if soup.select_one('div h2') else 'No Title')
        date_posted = txt_cleaner(soup.select_one('div.ReleaseDateSubHeaddateTime').get_text() if soup.select_one('div.ReleaseDateSubHeaddateTime') else 'No Date Provided')
        ministry = txt_cleaner(soup.select_one('div.MinistryNameSubhead').get_text() if soup.select_one('div.MinistryNameSubhead') else 'No Ministry Provided')


        log_info(f"Summarizing: {title}")
        content_length = len(content.split())
        max_length = min(1024, max(300, content_length // 2))
        min_length = max(20, max(200, content_length // 4))
        summary = summarize_text(content, max_length, min_length)
        # summary = "Union Minister for Education, Shri Dharmendra Pradhan, launched 41 new books under the PM YUVA 2.0 scheme at the New Delhi World Book Fair 2025. He praised the young authors, emphasized the scheme's impact on promoting Indian languages and literature, and announced initiatives to further this cause. The event was attended by dignitaries and highlighted the importance of literature in preserving cultural heritage."

        log_info(f"Summarization complete: {title}")

        img_src = [img.get('src') for img in soup.select('div.innner-page-main-about-us-content-right-part img')] or None
        
        iframe_src = [a['href'] for a in soup.select('div.innner-page-main-about-us-content-right-part blockquote.twitter-tweet a[href]')]

        tweet_links = [src for src in iframe_src if src.startswith('https://t.co/')]
        

        generated_images = search_images_from_content(summary,max_chunks=(audio_duration//4 - len(img_src)))

        img_src.extend(item['url'] for item in generated_images if not item['url'].startswith('https://lookaside'))

        log_info(f"Started Speeching of '{title}' for language 'english'")

        summary_audio = await generate_tts_audio_and_subtitles(summary, f"{title}", 'english')
        audio_duration = summary_audio.get("duration")
        
        log_success(f"Completed Speeching of '{title}' for language 'english'")
        
        log_info(f"Started Video Generation of '{title}' for language 'english'")

        video_path = f"output/{rename(title)}/english.mp4"

        create_video(images=img_src,audio_path=summary_audio.get("audio").lstrip('\\'),srt_path=summary_audio.get("subtitle").lstrip('\\'),ministry=ministry, output_path=video_path)

        log_success(f"Completed Video Generation of '{title}' for language 'english'")

        data = {
            'url': url,
            'images': img_src,
            'date_posted': parse_date_posted(date_posted),
            'tweets': tweet_links,
            'translations': {
                'english': {
                    'title': title,
                    'content': content,
                    'summary': summary,
                    'ministry': ministry,
                    'audio': summary_audio.get("audio").lstrip('\\').replace('\\','/'),
                    'video': video_path,
                    'subtitle': summary_audio.get("subtitle").lstrip('\\').replace('\\','/'),
                    'status': 'completed',
                }
            },
        }

        db_data = store_scraped_data_in_db(data)
        log_info(f"Scrape successful: {url}")
        return convert_object_ids(db_data)

    except requests.exceptions.RequestException as e:
        log_error(f"Network error scraping {url}: {e}")
        raise
    except Exception as e:
        log_error(f"Unexpected error scraping {url}: {e}")
        raise