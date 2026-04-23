from pydantic import BaseModel, Field
from typing import Optional

class NewsItem(BaseModel):
    title: str = Field(..., example="Breaking News Story")
    link: str = Field(..., example="https://example.com/story")
    pubDate: str = Field(..., example="2023-10-27T10:00:00Z")
    source: str = Field(..., example="Real News Network")
    logo: str = Field(..., example="https://example.com/logo.png")
    thumbnail: Optional[str] = Field(None, example="https://example.com/thumb.jpg")
    snippet: Optional[str] = Field(None, example="Here is a brief summary...")

class HealthStatus(BaseModel):
    status: str = Field("ok", example="ok")
