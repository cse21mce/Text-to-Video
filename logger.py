import logging

# Configure logging with colors and emoji
from termcolor import colored

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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