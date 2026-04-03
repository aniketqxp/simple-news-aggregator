# Feed: News Aggregator

Feed is a news aggregation service that provides a consolidated view of headlines using a FastAPI backend and a vanilla JavaScript frontend. It utilizes several technical strategies to retrieve, decode, and enrich article content in real time.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?style=flat-square&logo=fastapi&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-ES6+-F7DF1E?style=flat-square&logo=javascript&logoColor=black)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## Technical Features

- **Asynchronous Aggregation:** Headlines are retrieved from the Google News RSS feed. The backend processes these requests asynchronously to maintain low latency.
- **Content Resolution:** The service employs the `googlenewsdecoder` package to resolve obfuscated Google News redirect URLs into original publisher links.
- **Metadata Extraction:** Article pages are scraped using `newspaper4k` to extract high-resolution thumbnails and structured text snippets.
- **Frontend State Management:** An LRU (Least Recently Used) cache is implemented on the client side to manage topic switching and reduce redundant network requests.
- **Image Proxy Service:** A native FastAPI endpoint acts as a proxy for article images to address CORS restrictions and ensure consistent asset delivery.
- **Responsive Interface:** The frontend uses Tailwind CSS and Color Thief to provide a clean, modern interface where the visual theme adjusts based on the color palette of the featured article images.

---

## Architecture and Workflow

```text
Browser (Vanilla JS)
    │
    ├── GET /fetch-news?q={query}
    │       │
    │   FastAPI Backend
    │       ├── 1. Fetch Google News RSS 
    │       ├── 2. Decode redirect URLs via googlenewsdecoder 
    │       └── 3. Scrape article pages via newspaper4k
    │
    └── GET /proxy-image?url={encoded}
            │
        FastAPI Image Proxy (bypasses CORS)
```

### Operational Constraints

The enrichment pipeline relies on third-party services and publisher websites, which introduces specific technical boundaries:

1.  **Rate-Limiting:** The internal Google endpoints used for URL decoding can be subject to rate limits. When this occurs, the service will fall back to providing the original headline and link without rich metadata.
2.  **Anti-Scraping Measures:** Certain publishers use bot-detection services (such as Cloudflare) or authentication walls. In these cases, the scraper is unable to retrieve thumbnails or snippets.
3.  **Graceful Degradation:** The system is designed to handle these failures transparently. If enrichment fails, the core news content remains available through the RSS-derived data, and a status indicator in the UI informs the user of the reduced metadata availability.

---

## Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend** | Python 3.11+, FastAPI, Pydantic, Uvicorn |
| **Scraping** | BeautifulSoup4, newspaper4k, googlenewsdecoder |
| **Frontend** | HTML5, Vanilla JavaScript (ES6+), Tailwind CSS (CDN), Color Thief |
| **Deployment** | FastAPI StaticFiles for self-contained static asset serving |

---

## Installation

### Requirements
- Python 3.11 or higher

### Steps

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/aniketqxp/simple-news-aggregator.git
    cd simple-news-aggregator
    ```

2.  **Set up the environment:**
    ```bash
    python -m venv venv
    # Windows:
    venv\Scripts\activate
    # macOS / Linux:
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Start the server:**
    ```bash
    uvicorn app.main:app --reload
    ```

The application will be accessible at `http://127.0.0.1:8000`.

---

## Project Structure

```text
├── app/
│   ├── api/            # API endpoints and route logic
│   ├── core/           # Configuration and application settings
│   ├── models/         # Pydantic schemas for data validation
│   ├── services/       # RSS fetching, URL decoding, and scraping logic
│   └── main.py         # Application entry point and static file orchestration
├── static/
│   ├── css/            # Custom CSS files
│   ├── js/             # Frontend application logic
│   └── index.html      # Main HTML entry point
├── tests/              # Pytest-based integration tests
├── .gitignore
├── requirements.txt
└── README.md
```

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

Built by [Aniket Shinde](https://github.com/aniketqxp).
