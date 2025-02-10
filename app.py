from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

# User-defined modules
from scrap.scrap import scrape_press_release
from translate.translate import translate
from logger import log_info, log_warning, log_error, log_success, log_generator
from video.video import generate_video

# FastAPI app setup
app = FastAPI(
    title="PIB Press Releases Scraper",
    description="An API to Convert PIB press releases into Multilingual Video.",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Path to your output folder
output_folder_path = os.path.join(os.getcwd(), "output")

# Expose output folder to be accessed through the URL "/output"
app.mount("/output", StaticFiles(directory=output_folder_path), name="output")

@app.get("/", tags=["Root"])
def root():
    """Root endpoint"""
    log_info("Accessing the root endpoint")
    return {"message": "Welcome to PIB Press Releases To Multi-Lingual Video Generation API"}

@app.get("/text-to-video", tags=["Text to Video"])
async def text_to_video_endpoint(
    url: str = Query(..., description="The URL of the press release to convert into a multi-lingual video")
):
    """
    Convert a PIB press release into a multilingual video by:
    1. Scraping the press release content
    2. Translating it into multiple languages
    3. Streaming logs in real-time
    """
    try:
        if not url:
            log_warning("Empty URL provided")
            raise HTTPException(status_code=400, detail="URL is required")

        if not url.startswith("https://pib.gov.in"):
            log_warning(f"Invalid URL domain: {url}")
            raise HTTPException(status_code=400, detail="Invalid URL domain")

        log_info(f"Processing request for URL: {url}")

        # Scrape the press release
        press_release = await scrape_press_release(url)

        _id = press_release["_id"]
        title = press_release["translations"]["english"]["title"]
        summary = press_release["translations"]["english"]["summary"]
        content = press_release["translations"]["english"]["content"]
        ministry = press_release["translations"]["english"]["ministry"]
        images = press_release["images"]

        log_success(f"Scraped press release titled: {title}")

        # Translate the content
        log_info(f"Starting translation for Press Release titled: {title}")

        translations = await translate(
            _id=_id,
            title=title,
            summary=summary,
            content=content,
            ministry=ministry
        )

        translations.append(
            {
                "lang": 'english',
                "audio": press_release["translations"]["english"]["audio"],
                "subtitle": press_release["translations"]["english"]["subtitle"],
            }
        )

        log_success(f"Translation completed for: {title}")

        log_info(f"Video generation started for: {title}")
        print(translations)

        videos = await generate_video(
            title=title,
            images=images,
            translations=translations
        )

        log_success(f"Video generation completed for: {title}")

        return {
            "title": title,
            "videos": videos,
        }

    except Exception as e:
        log_error(f"Text to Video Processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stream-logs", tags=["Logs"])
async def stream_logs():
    return StreamingResponse(log_generator(), media_type="text/plain")

if __name__ == "__main__":
    log_info("🚀 Starting FastAPI application")
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
