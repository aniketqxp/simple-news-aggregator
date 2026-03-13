import logging
from collections import OrderedDict
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
import requests
from bs4 import BeautifulSoup
import urllib.parse
from urllib.parse import urlparse
import base64
import io
from googlenewsdecoder import gnewsdecoder
from newspaper import Article
import concurrent.futures
import time

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("feed")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Feed — News Aggregator API",
    description="Real-time news aggregation with article extraction and image proxying.",
    version="1.0.0",
)

# CORS — open for portfolio / demo use. Tighten for production deployments.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
REQUEST_TIMEOUT = 10  # seconds — for outbound HTTP requests
CACHE_EXPIRY_SECONDS = 1800  # 30 minutes
MAX_CACHE_ENTRIES = 500  # cap to prevent unbounded memory growth

# Blocklist patterns for known junk images
IMAGE_BLOCKLIST = [
    "spacer", "pixel", "blank", "tracking", "1x1",
    "data:image", "logo_og", "default_og",
]

# Domain blocklist: images from these domains are almost always generic logos
IMAGE_DOMAIN_BLOCKLIST = [
    "news.google.com", "lh3.googleusercontent.com",
    "fonts.gstatic.com", "www.google.com",
]

# Default User-Agent for outbound scraping requests
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# ---------------------------------------------------------------------------
# LRU-capped article cache
# ---------------------------------------------------------------------------
article_cache: OrderedDict[str, tuple[dict, float]] = OrderedDict()


def _cache_put(key: str, value: dict) -> None:
    """Insert into cache, evicting oldest entries if over the limit."""
    article_cache[key] = (value, time.time())
    if len(article_cache) > MAX_CACHE_ENTRIES:
        article_cache.popitem(last=False)


def _cache_get(key: str) -> dict | None:
    """Return cached value if present and not expired, else None."""
    if key in article_cache:
        data, ts = article_cache[key]
        if time.time() - ts < CACHE_EXPIRY_SECONDS:
            article_cache.move_to_end(key)  # refresh position
            return data
        else:
            del article_cache[key]
    return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def is_valid_image_url(img: str) -> bool:
    """Check if an image URL is likely a real hero image, not a tracker."""
    if not img or len(img) < 15:
        return False
    img_lower = img.lower()
    if any(kw in img_lower for kw in IMAGE_BLOCKLIST):
        return False
    try:
        domain = urlparse(img).netloc.lower()
        if any(blocked in domain for blocked in IMAGE_DOMAIN_BLOCKLIST):
            return False
    except Exception:
        return False
    return True


def harden_image_url(img: str, base_url: str) -> str:
    """Convert relative image URLs to absolute ones."""
    if img.startswith("//"):
        return "https:" + img
    elif img.startswith("/"):
        parsed = urlparse(base_url)
        return f"{parsed.scheme}://{parsed.netloc}{img}"
    elif not img.startswith("http"):
        parsed = urlparse(base_url)
        return f"{parsed.scheme}://{parsed.netloc}/{img}"
    return img


# ---------------------------------------------------------------------------
# Article extraction (with caching)
# ---------------------------------------------------------------------------
def fetch_and_parse_article(real_link: str) -> dict:
    """Download and parse an article, using the LRU cache."""
    cached = _cache_get(real_link)
    if cached is not None:
        return cached

    extracted: dict = {"thumbnail": None, "snippet": None}
    try:
        article = Article(real_link)
        article.download()
        article.parse()

        if article.top_image:
            img = harden_image_url(article.top_image, real_link)
            if is_valid_image_url(img):
                extracted["thumbnail"] = img

        if article.text and len(article.text.strip()) > 10:
            text = article.text.strip()
            extracted["snippet"] = text[:200] + ("..." if len(text) > 200 else "")

    except Exception as exc:
        logger.warning("Failed to parse article %s: %s", real_link, exc)

    if not extracted.get("thumbnail"):
        extracted["thumbnail"] = ""

    _cache_put(real_link, extracted)
    return extracted


# ---------------------------------------------------------------------------
# Process a single RSS <item>
# ---------------------------------------------------------------------------
def process_news_item(index: int, item) -> dict:
    title = item.title.text if item.title else "Untitled Story"
    link = item.link.text if item.link else "#"
    pub_date = item.pubDate.text if item.pubDate else ""
    source = item.source.text if item.source else ""

    # Favicon logo extraction
    source_url = item.source["url"] if item.source and item.source.has_attr("url") else ""
    if source_url:
        domain = urlparse(source_url).netloc
        logo = f"https://www.google.com/s2/favicons?domain={domain}&sz=128"
    else:
        logo = "https://ui-avatars.com/api/?name=News&background=222&color=fff&size=128"

    # Description fallback snippet
    description = item.description.text if item.description else ""
    desc_soup = BeautifulSoup(description, "html.parser")
    text_content = desc_soup.get_text(separator=" ", strip=True)
    fallback_snippet = text_content[:180] + "..." if len(text_content) > 180 else text_content
    if fallback_snippet.startswith("..."):
        fallback_snippet = fallback_snippet[3:].strip()
    if not fallback_snippet:
        fallback_snippet = "Click to read full story..."

    result_data = {
        "title": title,
        "link": link,
        "pubDate": pub_date,
        "source": source,
        "logo": logo,
        "thumbnail": "",
        "snippet": fallback_snippet,
    }

    # Decode the Google News redirect URL
    real_link = link
    try:
        decoded = gnewsdecoder(link, interval=1)
        if isinstance(decoded, dict):
            if decoded.get("status"):
                real_link = decoded["decoded_url"]
        elif isinstance(decoded, str):
            real_link = decoded
    except Exception as exc:
        logger.warning("Decoding error for %s: %s", link, exc)

    result_data["link"] = real_link

    # Fetch article content
    extracted_data = fetch_and_parse_article(real_link)

    if extracted_data.get("thumbnail"):
        result_data["thumbnail"] = extracted_data["thumbnail"]
    if extracted_data.get("snippet"):
        result_data["snippet"] = extracted_data["snippet"]

    return result_data


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
def health_check():
    """Lightweight health-check for deployment platforms."""
    return {"status": "ok"}


@app.get("/fetch-news")
def fetch_news(q: str = Query(..., description="Search query")):
    """Fetch and return news articles for the given query."""
    encoded_query = urllib.parse.quote(q)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

    try:
        response = requests.get(url, headers={"User-Agent": UA}, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Error fetching RSS feed for query '%s': %s", q, exc)
        raise HTTPException(status_code=502, detail="Failed to fetch news from upstream source.")

    soup = BeautifulSoup(response.content, "xml")
    items = soup.find_all("item")[:15]

    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        results = list(
            executor.map(
                lambda i_item: process_news_item(i_item[0], i_item[1]),
                enumerate(items),
            )
        )

    return results


@app.get("/proxy-image")
def proxy_image(url: str = Query(..., description="Base64-encoded image URL")):
    """Proxy an image server-side to bypass CORS and hotlink protection."""
    try:
        padded = url + "=" * (4 - len(url) % 4) if len(url) % 4 else url
        decoded_url = base64.urlsafe_b64decode(padded).decode("utf-8")
    except Exception:
        decoded_url = url  # Fallback if not base64-encoded

    try:
        resp = requests.get(
            decoded_url,
            timeout=5,
            headers={"User-Agent": UA},
            stream=True,
        )
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "image/jpeg")
        return StreamingResponse(
            io.BytesIO(resp.content),
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=86400",
                "Access-Control-Allow-Origin": "*",
            },
        )
    except Exception:
        # Return a 1×1 transparent GIF so the browser's onerror fires gracefully
        pixel = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")
        return StreamingResponse(io.BytesIO(pixel), media_type="image/gif")


# ---------------------------------------------------------------------------
# Static file serving (index.html, app.js, styles.css)
# ---------------------------------------------------------------------------
app.mount("/", StaticFiles(directory=".", html=True), name="static")