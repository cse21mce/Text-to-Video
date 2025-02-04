import asyncio
import aiohttp
import json
import torch

async def call_text_to_video_api(url):
    """
    Async function to call text-to-video API for a single URL
    
    Args:
        url (str): The press release URL to convert to video
    
    Returns:
        dict: Response from the API
    """
    api_endpoint = "http://127.0.0.1:8000/text-to-video"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(api_endpoint, params={'url': url}) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"Error processing {url}: Status code {response.status}")
                    return None
    
    except Exception as e:
        print(f"Exception occurred while processing {url}: {str(e)}")
        return None

async def process_urls(urls):
    """
    Process multiple URLs concurrently
    
    Args:
        urls (list): List of URLs to convert to video
    
    Returns:
        list: List of API responses
    """
    # Use asyncio.gather to run API calls concurrently
    tasks = [call_text_to_video_api(url) for url in urls]
    results = await asyncio.gather(*tasks)
    
    # Filter out None results
    return [result for result in results if result is not None]

# Example usage
async def main():
    # List of URLs to process
    urls = [
        "https://pib.gov.in/PressReleasePage.aspx?PRID=2095754",
        "https://pib.gov.in/PressReleasePage.aspx?PRID=2095694",
        "https://pib.gov.in/PressReleasePage.aspx?PRID=2095662",
        "https://pib.gov.in/PressReleasePage.aspx?PRID=2095661",
        "https://pib.gov.in/PressReleasePage.aspx?PRID=2095660"
    ]
    
    # Process URLs
    results = await process_urls(urls)
    
    # Print or process results
    for result in results:
        print(json.dumps(result, indent=2))

# Run the async main function
if __name__ == "__main__":
    # asyncio.run(main())
    pass