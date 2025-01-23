import asyncio
from playwright.async_api import async_playwright
import os
from datetime import datetime
from urllib.parse import unquote

async def capture_iframe(embed_url):
   curr_folder = os.path.dirname(os.path.abspath(__file__))
   output_dir = os.path.join(curr_folder, "tweets")
   if not os.path.exists(output_dir):
       os.makedirs(output_dir)

   async with async_playwright() as p:
       browser = await p.chromium.launch(headless=True)
       
       try:
           page = await browser.new_page()
           await page.set_viewport_size({"width": 550, "height": 600})
           await page.goto(unquote(embed_url), wait_until='networkidle')
           await page.wait_for_selector('article', timeout=10000)
           await page.wait_for_timeout(1000)
           
           tweet = await page.query_selector('article')
           if not tweet:
               print("Could not find tweet content")
               return None

           timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
           filename = f"tweet_{timestamp}.jpg"
           filepath = os.path.join(output_dir, filename)
           
           await tweet.screenshot(path=filepath)
           print(f"Screenshot saved to: {filepath}")
           return filepath
               
       except Exception as e:
           print(f"Error capturing tweet: {str(e)}")
           return None
           
       finally:
           await browser.close()
