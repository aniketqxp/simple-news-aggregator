# Feed — News Aggregator

A real-time news aggregator with a premium dark-mode interface. Built with FastAPI and vanilla JavaScript.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?style=flat-square&logo=fastapi&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-ES6+-F7DF1E?style=flat-square&logo=javascript&logoColor=black)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## What It Does

Feed pulls live headlines from the Google News RSS feed, then attempts to enrich each article with a high-resolution thumbnail and text snippet by scraping the original source page. The result is displayed in a responsive card grid with dynamic color accents, category chips, and smart caching.

**What always works:**
- Live headlines, publisher names, and logos
- Category search and topic chips
- Relative timestamps
- Frontend LRU caching for instant topic switching
- Image proxy that bypasses CORS restrictions

**What may be limited:**
- Thumbnails and article snippets (see limitations below)

---

## Known Limitations

This project runs into hard constraints that are not solvable within a standard open-source setup. The banner in the UI will appear when these limits are active.

### 1. Google News URL Decoding
Google News wraps article links in an obfuscated redirect format. Decoding these requires calling Google's internal `batchexecute` API via the [`googlenewsdecoder`](https://pypi.org/project/googlenewsdecoder/) library. Google **rate-limits** this endpoint aggressively. When rate-limited:
- The decoder returns an error instead of the real URL.
- The scraper has no valid URL to fetch and skips the article.
- Result: headlines load, thumbnails and snippets do not.

### 2. Publisher Anti-Scraping Policies
Even when decoding succeeds, many major publishers (NYT, WSJ, Bloomberg, The Atlantic) block automated requests at the HTTP level — Cloudflare challenges, paywall redirects, or bot-detection headers. `newspaper4k` cannot bypass these.

### 3. Subscription-Walled Content
Paywalled articles deliberately serve no meaningful content to unauthenticated scrapers. No image or description will be available regardless of the decoding method.

**The app communicates all of this honestly.** When extraction fails at scale, an amber banner appears informing the user that rich content is limited — not that the app is broken.

---

## Architecture

```
Browser (Vanilla JS)
    │
    ├── GET /fetch-news?q={query}
    │       │
    │   FastAPI Backend
    │       ├── Fetch Google News RSS (always works)
    │       ├── Decode redirect URLs via googlenewsdecoder (rate-limited)
    │       └── Scrape article pages via newspaper4k (publisher-dependent)
    │
    └── GET /proxy-image?url={encoded}
            │
        FastAPI Image Proxy (bypasses CORS)
```

---

## Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend** | Python 3.11+, FastAPI, Pydantic, Uvicorn |
| **Scraping** | BeautifulSoup4, newspaper4k, googlenewsdecoder |
| **Frontend** | HTML5, Vanilla JavaScript (ES6+), Tailwind CSS CDN, Color Thief |
| **Serving** | FastAPI StaticFiles (single-process, no separate static server needed) |

---

## Quick Start

### Prerequisites
- Python 3.11 or higher

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/aniketqxp/simple-news-aggregator.git
cd simple-news-aggregator

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000** in your browser.

> **Note:** Use Firefox or clear your browser cache if you don't see UI updates. Chrome aggressively caches static assets from localhost.

---

## Project Structure

```
├── app/
│   ├── api/            # FastAPI route handlers
│   ├── core/           # Config, constants, logger
│   ├── models/         # Pydantic schemas (NewsItem, HealthStatus)
│   ├── services/       # Business logic: RSS fetch, decode, scrape
│   └── main.py         # App entry point + static file mount
├── static/
│   ├── css/            # Custom styles
│   ├── js/             # app.js — all frontend logic
│   └── index.html      # Single-page entry point
├── tests/              # API integration tests (pytest + httpx)
├── .gitignore
├── requirements.txt
└── README.md
```

---

## License

MIT — see [LICENSE](LICENSE) for details.

---
Built by [Aniket Shinde](https://github.com/aniketqxp).
