# Feed — Minimalist News Aggregator

A high-performance, real-time news aggregator with a premium dark interface. Fetches live articles from Google News, extracts hero images and snippets on the fly, and renders them in a responsive card grid with dynamic color accents.

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?style=flat-square&logo=fastapi&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-ES6+-F7DF1E?style=flat-square&logo=javascript&logoColor=black)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-CDN-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

## Features

- **Real-Time Extraction** — Fetches and parses live articles directly from Google News RSS
- **Smart Image Proxying** — Bypasses CORS and hotlink protection by streaming images server-side
- **Intelligent Caching** — LRU-capped in-memory cache (backend) + per-category cache (frontend) for instant switching
- **Dynamic Color Accents** — Extracts dominant colors from hero images via Color Thief, applying ambient hover glows
- **Full-Bleed Card Grid** — Responsive layout where images fill the card, overlaid with text via gradient scrims
- **Keyboard Accessible** — Full keyboard navigation for the dropdown, chips, and card grid

## How It Works

```
┌─────────────┐      ┌──────────────────┐      ┌──────────────────┐
│   Browser    │ ───► │  FastAPI Backend  │ ───► │  Google News RSS  │
│  (app.js)    │ ◄─── │   (main.py)      │ ◄─── │  + newspaper3k   │
└─────────────┘      └──────────────────┘      └──────────────────┘
```

1. User searches or clicks a topic chip
2. Frontend sends a request to `/fetch-news?q=<query>`
3. Backend fetches the Google News RSS feed, decodes redirect URLs, and uses `newspaper3k` to extract hero images and text snippets
4. Results are cached (LRU, 30-min expiry) and returned as JSON
5. Frontend renders cards with mesh gradient fallbacks and proxied images via `/proxy-image`

## Tech Stack

| Layer    | Technology |
|----------|------------|
| Backend  | Python, FastAPI, uvicorn |
| Scraping | newspaper3k, BeautifulSoup, googlenewsdecoder |
| Frontend | Vanilla JS, Tailwind CSS (CDN), Color Thief |
| Serving  | FastAPI static file mount |

## Local Development

### Prerequisites
- Python 3.9+

### Setup
```bash
git clone https://github.com/aniketqxp/simple-news-aggregator.git
cd simple-news-aggregator
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

## Deployment

Feed requires a Python backend for scraping and image proxying — deploy as a **web service**, not a static site.

**Render / Railway / Heroku:**
1. Connect the repository
2. Build command: `pip install -r requirements.txt`
3. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

The `/health` endpoint returns `{"status": "ok"}` for platform health checks.

## License

MIT — see [LICENSE](LICENSE) for details.
