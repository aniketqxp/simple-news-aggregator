from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
import requests
from bs4 import BeautifulSoup
import urllib.parse
from urllib.parse import urlparse
import base64
import io
from googlenewsdecoder import decoderv1
from newspaper import Article
import concurrent.futures
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Blocklist patterns for known junk images
IMAGE_BLOCKLIST = ["spacer", "pixel", "blank", "tracking", "1x1", "data:image", "logo_og", "default_og"]

# Domain blocklist: images from these domains are almost always generic logos, not article heroes
IMAGE_DOMAIN_BLOCKLIST = ["news.google.com", "lh3.googleusercontent.com", "fonts.gstatic.com", "www.google.com"]

# Global article cache: maps real_url -> (extracted_data, timestamp)
article_cache = {}
CACHE_EXPIRY_SECONDS = 1800  # 30 minutes

def is_valid_image_url(img):
    """Check if image URL is likely to be a real hero image, not a tracker or placeholder."""
    if not img or len(img) < 15:
        return False
    img_lower = img.lower()
    if any(keyword in img_lower for keyword in IMAGE_BLOCKLIST):
        return False
    # Check domain blocklist
    try:
        domain = urlparse(img).netloc.lower()
        if any(blocked in domain for blocked in IMAGE_DOMAIN_BLOCKLIST):
            return False
    except Exception:
        return False
    return True

def harden_image_url(img, base_url):
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

def fetch_and_parse_article(real_link, index):
    """Download and parse an article, with caching."""
    now = time.time()
    if real_link in article_cache:
        cached_data, timestamp = article_cache[real_link]
        if now - timestamp < CACHE_EXPIRY_SECONDS:
            return cached_data

    extracted = {"thumbnail": None, "snippet": None}
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

    except Exception as e:
        print(f"Failed to parse article {real_link}: {e}")

    # If no valid thumbnail was found, leave it empty — frontend handles the visual fallback
    if not extracted.get("thumbnail"):
        extracted["thumbnail"] = ""

    # Cache the result
    article_cache[real_link] = (extracted, now)
    return extracted

def process_news_item(index, item):
    title = item.title.text if item.title else "Untitled Story"
    link = item.link.text if item.link else "#"
    pub_date = item.pubDate.text if item.pubDate else ""
    source = item.source.text if item.source else ""

    # Favicon logo extraction
    source_url = item.source['url'] if item.source and item.source.has_attr('url') else ""
    if source_url:
        domain = urlparse(source_url).netloc
        logo = f"https://www.google.com/s2/favicons?domain={domain}&sz=128"
    else:
        logo = "https://ui-avatars.com/api/?name=News&background=222&color=fff&size=128"

    # Get initial description fallback snippet
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
        "snippet": fallback_snippet
    }

    # Decode the Google News redirect
    real_link = link
    try:
        decoded = decoderv1(link)
        if decoded and decoded.get("status"):
            real_link = decoded["decoded_url"]
    except Exception:
        pass

    result_data["link"] = real_link

    # Delegate to the cached parse function
    extracted_data = fetch_and_parse_article(real_link, index)

    if extracted_data.get("thumbnail"):
        result_data["thumbnail"] = extracted_data["thumbnail"]
    if extracted_data.get("snippet"):
        result_data["snippet"] = extracted_data["snippet"]

    return result_data

@app.get("/fetch-news")
def fetch_news(q: str = Query(..., description="Search query")):
    encoded_query = urllib.parse.quote(q)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching news: {e}")
        return []

    soup = BeautifulSoup(response.content, "xml")
    items = soup.find_all("item")[:15]

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        results = list(executor.map(lambda i_item: process_news_item(i_item[0], i_item[1]), enumerate(items)))

    return results

@app.get("/proxy-image")
def proxy_image(url: str = Query(..., description="Base64-encoded image URL")):
    """Fetch an image server-side and stream it to the browser, bypassing hotlink protection."""
    try:
        # Re-add padding stripped by frontend
        padded = url + '=' * (4 - len(url) % 4) if len(url) % 4 else url
        decoded_url = base64.urlsafe_b64decode(padded).decode('utf-8')
    except Exception:
        decoded_url = url  # Fallback if not encoded
    
    try:
        resp = requests.get(decoded_url, timeout=5, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }, stream=True)
        resp.raise_for_status()
        
        content_type = resp.headers.get('Content-Type', 'image/jpeg')
        return StreamingResponse(
            io.BytesIO(resp.content),
            media_type=content_type,
            headers={'Cache-Control': 'public, max-age=86400'}  # Cache for 24h
        )
    except Exception:
        # Return a 1x1 transparent pixel so onerror fires in the browser
        pixel = base64.b64decode('R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7')
        return StreamingResponse(io.BytesIO(pixel), media_type='image/gif')

# Serve static files (index.html, app.js, etc.)
app.mount("/", StaticFiles(directory=".", html=True), name="static")