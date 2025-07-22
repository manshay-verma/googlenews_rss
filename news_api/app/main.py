from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import feedparser
from functools import lru_cache
import time

# -------- CONFIG --------
RSS_BASE = "https://news.google.com/rss"
LANGUAGE = "en"
COUNTRY = "IN"
CEID = f"{COUNTRY}:{LANGUAGE}"

# -------- MODEL --------
class NewsItem(BaseModel):
    title: str
    link: str
    published: str
    summary: str

class MetaInfo(BaseModel):
    service: str
    status: str
    timestamp: float

# -------- CACHING --------
@lru_cache(maxsize=64)
def cached_fetch_news(query: Optional[str] = None, category: Optional[str] = None):
    print("⚡ Fetching fresh data...")  # Helps to track in logs
    return _fetch_news(query, category)

# -------- SERVICE --------
def _fetch_news(query: Optional[str] = None, category: Optional[str] = None):
    if query:
        query = query.replace(" ", "+")
        url = f"{RSS_BASE}/search?q={query}&hl={LANGUAGE}-{COUNTRY}&gl={COUNTRY}&ceid={CEID}"
    elif category:
        url = f"{RSS_BASE}/headlines/section/topic/{category.upper()}?hl={LANGUAGE}-{COUNTRY}&gl={COUNTRY}&ceid={CEID}"
    else:
        url = f"{RSS_BASE}?hl={LANGUAGE}-{COUNTRY}&gl={COUNTRY}&ceid={CEID}"

    feed = feedparser.parse(url)
    if not feed.entries:
        raise HTTPException(status_code=404, detail="No news found or feed parsing failed.")
    
    return [
        {
            "title": entry.title,
            "link": entry.link,
            "published": entry.published,
            "summary": entry.summary
        }
        for entry in feed.entries
    ]

# -------- APP --------
app = FastAPI(title="News API with Caching")

@app.get("/today", response_model=List[NewsItem])
def get_today_news():
    return cached_fetch_news()

@app.get("/search", response_model=List[NewsItem])
def search_news(q: str = Query(..., description="Search topic")):
    return cached_fetch_news(query=q)

@app.get("/category/{name}", response_model=List[NewsItem])
def get_by_category(name: str):
    return cached_fetch_news(category=name)

@app.get("/meta", response_model=MetaInfo)
def get_meta():
    return {
        "service": "Google News RSS FastAPI",
        "status": "OK",
        "timestamp": time.time()
    }
