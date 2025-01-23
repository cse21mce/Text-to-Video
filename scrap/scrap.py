
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from urllib.parse import urljoin

# User defined modules
from utils import convert_object_ids
from database.db import store_scraped_data_in_db, is_url_scraped
from summarize.summarize import summarize_text
from speech.tts import generate_tts_audio_and_subtitles
from logger import log_info, log_warning, log_error  
from image.image_search import search_images_from_content

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
    Scrapes detailed information from a single press release URL.
    """
    try:
        scraped_data = is_url_scraped(url)
        if(scraped_data != None):
            log_info(f"Skipping already scraped URL: {url}")
            return convert_object_ids(scraped_data)
        
        log_info(f"Scraping Started for URL: {url}")  

        headers = {
            'User-Agent': 'Mozilla/5.0',
        }
        response = session.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        print(f'\n\n {soup} \n\n')
        
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
        log_info(f"Completed Summarizing Press Release: {title}")

        # Extract images and iframes
        img_src = [img.get('src') for img in soup.select('div.innner-page-main-about-us-content-right-part img')] or None

        # Extract iframes
        # # Extract iframes including Twitter embeds
        iframes = soup.select('div.innner-page-main-about-us-content-right-part iframe, div.innner-page-main-about-us-content-right-part blockquote.twitter-tweet')
        iframe_src = []
        for iframe in iframes:
            if iframe.name == 'iframe' and iframe.has_attr('src'):
                iframe_src.append(iframe['src'])
            elif iframe.get('class') == ['twitter-tweet']:
                # For Twitter embeds, get the tweet URL
                tweet_link = iframe.find('a', href=True)
                if tweet_link:
                    iframe_src.append(tweet_link['href'])

        # Generate TTS
        summary_audio = await generate_tts_audio_and_subtitles(summary, f"{title}", 'english')
        # content_audio = await generate_tts_audio_and_subtitles(content, f"content_{title}", 'english')

        data = {
            'date_posted': date_posted,
            'images': img_src,
            'iframes': iframe_src,
            'url': url,
            "generated_images": generated_images,
            'translations': {
                'english': {
                    'title': title,
                    'summary': summary,
                    'ministry': ministry,
                    'content': content,
                    'audio': summary_audio.get("audio"),
                    'subtitle': summary_audio.get("subtitle"),
                    # 'content_audio': content_audio.get("audio"),
                    # 'content_subtitle': content_audio.get("subtitle"),
                    'status': 'completed',
                }
            },
        }

        db_data = store_scraped_data_in_db(data)

        log_info(f"Successfully Scraped data from {url}")
        return convert_object_ids(db_data)

    except Exception as e:
        log_error(f"Error scraping press release from {url}: {e}")
        return None
