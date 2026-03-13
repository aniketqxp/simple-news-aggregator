# Feed — Minimalist News Aggregator

A high-performance, real-time news aggregator built with a focus on extreme minimalism, dense information architecture, and a premium "Linear-style" aesthetic.

![Feed UI Screenshot](.github/assets/screenshot.png) <!-- Note: We will add a screenshot here later -->

## Architecture

Feed is designed as a single-page application served directly by a Python backend:

- **Frontend**: Pure HTML, Vanilla JS, and Tailwind CSS (via CDN). No heavy client-side frameworks.
- **Backend**: FastAPI (Python). Handles real-time scraping, Google News URL decoding, and image proxying.
- **Scraping Engine**: `newspaper3k` and `googlenewsdecoder` extract full article snippets and hero images on the fly.
- **Design System**: Monochrome zinc palette, Inter font, custom dropdown components, and Color Thief for dynamic hover accents.

## Features

- **Real-Time Extraction**: Fetches and parses live articles directly from Google News.
- **Smart Image Proxying**: Bypasses strict CORS and hotlink protection by proxying images server-side.
- **Intelligent Caching**: In-memory caching on both the backend (to prevent redundant scraping) and frontend (for instant category switching).
- **Dynamic Color Accents**: Uses `color-thief.js` to extract dominant colors from hero images, applying them as subtle ambient hover glows.
- **Responsive "Full-Bleed" Grid**: Modern card layout where the image fills the card, overlaid with text via a gradient scrim.

## Local Development

### Prerequisites
- Python 3.9+ 

### Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/aniketqxp/simple-news-aggregator.git
   cd simple-news-aggregator
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the development server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

4. Open your browser to `http://127.0.0.1:8000`

## Deployment

Because Feed relies on a Python backend for scraping and proxying, it should be deployed as a **Web Service** on platforms like Render, Railway, or Heroku, rather than a static site host.

1. Connect your repository to your cloud provider.
2. Ensure the build command installs dependencies (`pip install -r requirements.txt`).
3. Set the start command to:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

## License
MIT License
