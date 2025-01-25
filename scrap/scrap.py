
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import asyncio

# User defined modules
from utils import convert_object_ids
from database.db import store_scraped_data_in_db, is_url_scraped
from summarize.summarize import summarize_text
from speech.tts import generate_tts_audio_and_subtitles
from logger import log_info, log_warning, log_error  
from image.image_search import search_images_from_content
from image.capture_iframe import capture_iframe
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

# Use asyncio.gather for parallel processing
async def process_iframe(iframe):
    if iframe.name == 'iframe' and iframe.has_attr('src'):
        return iframe['src']
    elif iframe.get('class') == ['twitter-tweet']:
        tweet_link = iframe.find('a', href=True)
        if tweet_link:
            # log_info(f"Processing tweet: {tweet_link['href']}")
            # img_path = await capture_iframe(tweet_link['href'])
            # if img_path:
            #     captured_images.append(img_path)
            return tweet_link['href']
    return None

async def scrape_press_release(url: str):
    """
    Scrapes detailed information from a single press release URL.
    
    Args:
        url (str): URL of the press release
        
    Returns:
        dict: Scraped and processed data
    """
    try:
        
        # Check cache first
        scraped_data = is_url_scraped(url)
        if scraped_data:
            log_info(f"Retrieved cached data for URL: {url}")
            return convert_object_ids(scraped_data)
        
        log_info(f"Starting fresh scrape for URL: {url}")
        
        # Initialize session with retry mechanism
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
        # save_html_to_file(soup)

        
        # Extract text from paragraphs within the main content section
        all_text = ' '.join([p.get_text() for p in soup.select('.innner-page-main-about-us-content-right-part p')]).strip()

        # Extract title
        title = txt_cleaner(soup.select_one('div h2').get_text() if soup.select_one('div h2') else 'No Title')

        # Extract date posted
        date_posted = txt_cleaner(soup.select_one('div.ReleaseDateSubHeaddateTime').get_text() if soup.select_one('div.ReleaseDateSubHeaddateTime') else 'No Date Provided')

        # Extract ministry
        ministry =  txt_cleaner(soup.select_one('div.MinistryNameSubhead').get_text() if soup.select_one('div.MinistryNameSubhead') else 'No Ministry Provided')

        # Extract content
        content = txt_cleaner(all_text)


        generated_images = search_images_from_content(content)
        

        # Summarize the content
        log_info(f"Started Summarizing Press Release: {title}")
        content_length = len(content.split())

        max_length = min(1024, max(300, content_length // 2))
        min_length = max(20, max(200, content_length // 4))

        summary = summarize_text(content, max_length, min_length)
        # summary = ''
        log_info(f"Completed Summarizing Press Release: {title}")


        # # Extract iframes including Twitter embeds
        # iframes = soup.select('div.innner-page-main-about-us-content-right-part iframe, div.innner-page-main-about-us-content-right-part blockquote.twitter-tweet')
        # iframe_src = []
        # for iframe in iframes:
        #     if iframe.name == 'iframe' and iframe.has_attr('src'):
        #         iframe_src.append(iframe['src'])
        #     elif iframe.get('class') == ['twitter-tweet']:
        #         # For Twitter embeds, get the tweet URL
        #         tweet_link = iframe.find('a', href=True)
        #         if tweet_link:
        #             iframe_src.append(tweet_link['href'])
        #             print(f"Tweet link: {tweet_link['href']}")
        #             img_path = await capture_iframe(tweet_link['href'])
        #             log_warning(f"Captured iframe: {img_path}")
        #             iframe_src.append(img_path)
        

        # Extract images
        img_src = [img.get('src') for img in soup.select('div.innner-page-main-about-us-content-right-part img')] or None
        
        # Extract iframes including Twitter embeds
        # iframes = soup.select('div.innner-page-main-about-us-content-right-part iframe, div.innner-page-main-about-us-content-right-part blockquote.twitter-tweet a')
        # iframe_src = [iframe['href'] for iframe in iframes]
        # captured_images = []

        
        # # Process iframes in parallel
        # iframe_tasks = [process_iframe(iframe) for iframe in iframes]
        # iframe_results = await asyncio.gather(*iframe_tasks)
        # iframe_src = [result for result in iframe_results if result]

        # print(f"Captured images: {captured_images}")

        # Generate TTS
        summary_audio = await generate_tts_audio_and_subtitles(summary, f"{title}", 'english')
        # content_audio = await generate_tts_audio_and_subtitles(content, f"content_{title}", 'english')

        data = {
            'url': url,
            # 'iframes': iframe_src,
            'pib_images': img_src,
            "generated_images": generated_images,
            'date_posted': date_posted,
            'translations': {
                'english': {
                    'title': title,
                    'summary': summary,
                    'ministry': ministry,
                    'content': content,
                    'audio': summary_audio.get("audio"),
                    'subtitle': summary_audio.get("subtitle"),
                    'status': 'completed',
                }
            },
        }

        db_data = store_scraped_data_in_db(data)

        log_info(f"Successfully Scraped data from {url}")
        return convert_object_ids(db_data)

    except requests.exceptions.RequestException as e:
        log_error(f"Network error while scraping {url}: {e}")
        raise
    except Exception as e:
        log_error(f"Unexpected error while scraping {url}: {e}")
        raise
