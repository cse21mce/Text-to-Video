from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import uvicorn
import logging

# User defined modules
from scrap.scrap import scrape_press_release
from summarize.summarize import summarize_text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="PIB Press Releases Scraper", description="An API to scrape PIB press releases.", version="1.0.0")


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins, you can specify a list of allowed origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)


@app.get("/", tags=["Root"])
def root():
    return {"message": "Welcome to PIB Press Releases To Multi-Lingual Video Generation API"}


@app.get("/text-to-video", tags=["Text to Video"])
def text_to_video_endpoint(url: str = Query(..., description="The URL of the press release to covert into multi-lingual video")):
    """
    Convert text to multi-lingual video from the provided URL.
    """
    try:
        if url is None:
            raise HTTPException(status_code=404, detail="No URL provided.")
        elif url == "":
            raise HTTPException(status_code=404, detail="Empty URL provided.")
        
        logger.info(f"Starting text to video for URL: {url}")
        _id,title,date_posted,ministry,content,images = scrape_press_release(url)
        
        logger.info(f"Started Summarising Press Release : {title}")
        # Summarize the content
        summary = summarize_text(content)

        logger.info(f"Started Translating Press Release : {title}")
        

        
    except Exception as e:
        logger.error(f"Error converting text to video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # Run the FastAPI application on the specified host and port with auto-reloading enabled
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)