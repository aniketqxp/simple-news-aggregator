from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check_endpoint():
    """Verify that the /health endpoint returns successfully."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_static_files_loading():
    """Verify that the frontend entry point is served from the root."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Feed — News Aggregator" in response.text

def test_fetch_news_requires_query():
    """Verify that the /fetch-news endpoint requires a 'q' parameter."""
    response = client.get("/fetch-news")
    assert response.status_code == 422  # Unprocessable Entity (Missing required query param)
