import logging
import os

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("feed")

# ---------------------------------------------------------------------------
# Application Constants
# ---------------------------------------------------------------------------
APP_TITLE = "Feed — News Aggregator API"
APP_DESCRIPTION = "Real-time news aggregation with article extraction and image proxying."
APP_VERSION = "1.0.0"

REQUEST_TIMEOUT = 10  # seconds — for outbound HTTP requests
CACHE_EXPIRY_SECONDS = 1800  # 30 minutes
MAX_CACHE_ENTRIES = 500  # cap to prevent unbounded memory growth

# Default User-Agent for outbound scraping requests
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# ---------------------------------------------------------------------------
# Image Filtering
# ---------------------------------------------------------------------------
IMAGE_BLOCKLIST = [
    "spacer", "pixel", "blank", "tracking", "1x1",
    "data:image", "logo_og", "default_og",
]

IMAGE_DOMAIN_BLOCKLIST = [
    "news.google.com", "lh3.googleusercontent.com",
    "fonts.gstatic.com", "www.google.com",
]
