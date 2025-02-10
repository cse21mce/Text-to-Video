import logging
import io
import sys
import asyncio
from termcolor import colored
from fastapi.responses import StreamingResponse

# Configure logging to display in the terminal
log_stream = io.StringIO()  # Keeps in-memory log output for streaming
log_handler = logging.StreamHandler(sys.stdout)  # Log to stdout (console)
log_handler.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
log_handler.setFormatter(formatter)

# Add a StringIO handler for capturing logs to stream
string_handler = logging.StreamHandler(log_stream)
string_handler.setLevel(logging.INFO)
string_handler.setFormatter(formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)
logger.addHandler(string_handler)  # Add the StringIO handler

# Async function to stream logs
async def log_generator():
    while True:
        log_stream.seek(0)  # Go to the beginning of the log buffer
        logs = log_stream.read()  # Read the content
        log_stream.truncate(0)  # Clear the buffer after reading
        if logs:
            yield logs  # Yield logs to StreamingResponse
        await asyncio.sleep(0.1)  # Adjust delay for responsiveness

# Log messages with color and emoji
def log(message: str):
    logger.info(f"==> {message}")

def log_info(message: str):
    logger.info(colored(f"🔹 {message}", "blue"))

def log_success(message: str):
    logger.info(colored(f"✅ {message}", "green"))

def log_warning(message: str):
    logger.warning(colored(f"⚠️ {message}", "yellow"))

def log_error(message: str):
    logger.error(colored(f"❌ {message}", "red"))

