from playwright.async_api import async_playwright
import os
from datetime import datetime
from urllib.parse import unquote

async def capture_iframe(embed_url):
    """
    Capture screenshot of a tweet from its embed URL.

    Args:
        embed_url (str): URL of the embedded tweet.

    Returns:
        str: Path to the saved screenshot, or None if failed.
    """
    curr_folder = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(curr_folder, "tweets")
    os.makedirs(output_dir, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.set_viewport_size({"width": 550, "height": 600})
            await page.goto(unquote(embed_url), wait_until='networkidle')
            await page.wait_for_selector('article', timeout=20000)
            await page.wait_for_timeout(5000)
            
            tweet = await page.query_selector('article')
            if not tweet:
                print("Could not find tweet content")
                return None

            filename = f"tweet_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            filepath = os.path.join(output_dir, filename)
            
            await tweet.screenshot(path=filepath)
            print(f"Screenshot saved to: {filepath}")
            return filepath
                
        except Exception as e:
            print(f"Error capturing tweet: {str(e)}")
            return None
        finally:
            await browser.close()



# if __name__ == "__main__":
#     import asyncio
#     example_embed_url = f"https://t.co/aewpSJixkT"
#     asyncio.run(capture_iframe(example_embed_url))