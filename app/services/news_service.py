import time
import requests
import urllib.parse
from typing import Optional, List, Dict, Tuple
from collections import OrderedDict
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from googlenewsdecoder import decoderv3 as gnewsdecoder
from newspaper import Article
import concurrent.futures

from app.core.config import (
    logger, UA, REQUEST_TIMEOUT, CACHE_EXPIRY_SECONDS, MAX_CACHE_ENTRIES,
    IMAGE_BLOCKLIST, IMAGE_DOMAIN_BLOCKLIST
)

# ---------------------------------------------------------------------------
# LRU Cache
# ---------------------------------------------------------------------------
article_cache: OrderedDict[str, Tuple[Dict, float]] = OrderedDict()

def _cache_put(key: str, value: Dict) -> None:
    article_cache[key] = (value, time.time())
    if len(article_cache) > MAX_CACHE_ENTRIES:
        article_cache.popitem(last=False)

def _cache_get(key: str) -> Optional[Dict]:
    if key in article_cache:
        data, ts = article_cache[key]
        if time.time() - ts < CACHE_EXPIRY_SECONDS:
            article_cache.move_to_end(key)
            return data
        else:
            del article_cache[key]
    return None

# ---------------------------------------------------------------------------
# Image Validation
# ---------------------------------------------------------------------------
def harden_image_url(img: str, base_url: str) -> str:
    """Resolve relative/protocol-relative URLs to absolute HTTPS."""
    if img.startswith("//"): return "https:" + img
    if img.startswith("/"):
        p = urlparse(base_url)
        return f"{p.scheme}://{p.netloc}{img}"
    if not img.startswith("http"):
        p = urlparse(base_url)
        return f"{p.scheme}://{p.netloc}/{img}"
    return img

def is_valid_image_url(img: str) -> bool:
    """Filter out known-bad images (tracking pixels, logos, icons, etc.)."""
    if not img or len(img) < 15: return False
    low = img.lower()
    if any(k in low for k in IMAGE_BLOCKLIST): return False
    try:
        dom = urlparse(img).netloc.lower()
        if any(b in dom for b in IMAGE_DOMAIN_BLOCKLIST): return False
    except: return False
    return True

# ---------------------------------------------------------------------------
# Article Extraction
# ---------------------------------------------------------------------------
def fetch_and_parse_article(real_link: str) -> Dict:
    """
    Downloads and parses a news article for its hero image and text snippet.

    Note: Extraction success depends on the publisher's site structure and
    anti-scraping policies. Subscription-walled and heavily protected sites
    will return empty results by design.
    """
    cached = _cache_get(real_link)
    if cached: return cached

    data = {"thumbnail": "", "snippet": ""}
    try:
        article = Article(real_link, browser_user_agent=UA)
        article.download()
        article.parse()

        if article.top_image:
            img = harden_image_url(article.top_image, real_link)
            if is_valid_image_url(img):
                data["thumbnail"] = img

        if article.text:
            cleaned = article.text.strip().replace("\n", " ")
            data["snippet"] = cleaned[:200] + "..." if len(cleaned) > 200 else cleaned

    except Exception as e:
        logger.warning(f"Extraction failed for {real_link[:60]}: {e}")

    _cache_put(real_link, data)
    return data

# ---------------------------------------------------------------------------
# Per-Item Processing
# ---------------------------------------------------------------------------
def process_news_item(index: int, item) -> Dict:
    """
    Processes a single RSS item:
    1. Decodes the obfuscated Google News redirect URL.
    2. Scrapes the real article page for a thumbnail and snippet.

    Step 1 depends on the `googlenewsdecoder` library successfully calling
    Google's internal batchexecute API. This is subject to rate-limiting.
    Step 2 depends on the publisher allowing scraping.
    """
    title = item.title.text if item.title else "Untitled Story"
    link = item.link.text if item.link else "#"
    pub_date = item.pubDate.text if item.pubDate else ""
    source = item.source.text if item.source else ""

    source_url = item.source["url"] if item.source and item.source.has_attr("url") else ""
    logo = (
        f"https://www.google.com/s2/favicons?domain={urlparse(source_url).netloc}&sz=128"
        if source_url
        else "https://ui-avatars.com/api/?name=News&background=222&color=fff&size=128"
    )

    # RSS description as snippet fallback (always available)
    description = item.description.text if item.description else ""
    desc_soup = BeautifulSoup(description, "html.parser")
    text_content = desc_soup.get_text(separator=" ", strip=True)
    fallback_snippet = text_content[:180] + "..." if len(text_content) > 180 else text_content
    if not fallback_snippet or fallback_snippet.startswith("..."):
        fallback_snippet = "Click to read the full story."

    final_item = {
        "title": title,
        "link": link,
        "pubDate": pub_date,
        "source": source,
        "logo": logo,
        "thumbnail": "",
        "snippet": fallback_snippet,
    }

    # --- Step 1: Decode Google News redirect URL ---
    real_link = link
    decode_ok = False

    if "news.google.com" in link:
        try:
            decoded = gnewsdecoder(link)
            if isinstance(decoded, dict) and decoded.get("status"):
                real_link = decoded.get("decoded_url") or decoded.get("url") or link
                decode_ok = True
            elif isinstance(decoded, str) and decoded.startswith("http"):
                real_link = decoded
                decode_ok = True
            else:
                logger.warning(f"Decoder returned unexpected format for {link[:60]}")
        except Exception as e:
            logger.warning(f"URL decoding failed for {link[:60]}: {e}")
    else:
        # Direct link — no decoding needed
        real_link = link
        decode_ok = True

    final_item["link"] = real_link

    # --- Step 2: Scrape for thumbnail and better snippet ---
    if decode_ok:
        meta = fetch_and_parse_article(real_link)
        if meta["thumbnail"]:
            final_item["thumbnail"] = meta["thumbnail"]
        if meta["snippet"]:
            final_item["snippet"] = meta["snippet"]

    return final_item

# ---------------------------------------------------------------------------
# Main Fetch (Parallel with conservative concurrency)
# ---------------------------------------------------------------------------
def fetch_news_results(query: str, limit: int = 15) -> List[Dict]:
    """
    Fetches news from the Google News RSS feed and enriches each item.

    Concurrency is capped at 5 workers to reduce the risk of triggering
    Google's rate-limiting on the URL decoder API.
    """
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

    try:
        response = requests.get(url, headers={"User-Agent": UA}, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"RSS fetch failed: {e}")
        return []

    soup = BeautifulSoup(response.content, "xml")
    items = soup.find_all("item")[:limit]

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(lambda x: process_news_item(x[0], x[1]), enumerate(items)))

    return results
