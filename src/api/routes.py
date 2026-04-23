import io
import base64
import requests
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
from typing import List

from src.core.config import UA, logger
from src.models.news import NewsItem, HealthStatus
from src.services.news_service import fetch_news_results

router = APIRouter()

@router.get("/health", response_model=HealthStatus)
def health_check():
    """Lightweight health-check for deployment platforms."""
    return {"status": "ok"}


@router.get("/fetch-news", response_model=List[NewsItem])
def fetch_news(q: str = Query(..., description="Search query")):
    """Fetch and return news articles for the given query."""
    results = fetch_news_results(q)
    if not results:
        raise HTTPException(status_code=502, detail="Failed to fetch news from upstream source.")
    return results


@router.get("/proxy-image")
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
