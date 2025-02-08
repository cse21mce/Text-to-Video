import io
import logging
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# User defined modules
from scrap.scrap import scrape_press_release
from translate.translate import translate
from video.create_video import generate_video
from logger import log_info, log_warning, log_error, log_success

# FastAPI app setup
app = FastAPI(title="PIB Press Releases Scraper", description="An API to Convert PIB press releases into Multilingual Video.", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins, you can specify a list of allowed origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Create an in-memory log stream
log_stream = io.StringIO()
log_handler = logging.StreamHandler(log_stream)
log_handler.setLevel(logging.INFO)
logger = logging.getLogger(__name__)
logger.addHandler(log_handler)


@app.get("/", tags=["Root"])
def root():
    log_info("Accessing the root endpoint")
    return {"message": "Welcome to PIB Press Releases To Multi-Lingual Video Generation API"}



@app.get("/text-to-video", tags=["Text to Video"])
async def text_to_video_endpoint(
    url: str = Query(
        ..., 
        description="The URL of the press release to convert into a multi-lingual video"
    )
):
    """
    Convert press release text to multi-lingual video.
    
    Args:
        url (str): The URL of the press release
        
    Returns:
        StreamingResponse: Log stream of the conversion process
        
    Raises:
        HTTPException: If URL is invalid or processing fails
    """
    try:
        if not url:
            log_warning("Empty URL provided")
            raise HTTPException(status_code=400, detail="URL is required")
            
        if not url.startswith('https://pib.gov.in'):
            log_warning(f"Invalid URL domain: {url}")
            raise HTTPException(status_code=400, detail="Invalid URL domain")
            
        log_info(f"Processing request for URL: {url}")
        
        # Scrap the press release
        press_release = await scrape_press_release(url)

        _id = press_release["_id"]
        title = press_release["translations"]["english"]["title"]
        summary=press_release['translations']['english']['summary']
        ministry=press_release['translations']['english']['ministry']

        log_success(f"Scraped press release titled: {title}")

        # Translate the content 
        log_info(f"Starting translation for Press Release titled: {title}")

        # return translated text and audio
        translations = await translate(
            _id=_id,
            title=title,
            summary=summary,
            ministry=ministry
        )

        log_success(f"Translation completed for: {title}")

        # Generate the Video
        log_success(f"Video Generation Started for: {title}")

        await generate_video(
            _id=_id,
            translations=translations,
        )

        log_success(f"Video Generation Completed for: {title}")

    except Exception as e:
        log_error(f"Text to Video Processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


    # Reset the log stream position and stream the logs as the response
    log_stream.seek(0)
    return StreamingResponse(log_stream, media_type="text/plain")


if __name__ == "__main__":
    log_info("🚀 Starting FastAPI application")
    # Run the FastAPI application with auto-reloading enabled
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
