# main.py
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import feedparser

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

# -------- SERVICE --------
def fetch_news(query: Optional[str] = None, category: Optional[str] = None):
    if query:
        query = query.replace(" ", "+")
        url = f"{RSS_BASE}/search?q={query}&hl={LANGUAGE}-{COUNTRY}&gl={COUNTRY}&ceid={CEID}"
    elif category:
        url = f"{RSS_BASE}/headlines/section/topic/{category.upper()}?hl={LANGUAGE}-{COUNTRY}&gl={COUNTRY}&ceid={CEID}"
    else:
        url = f"{RSS_BASE}?hl={LANGUAGE}-{COUNTRY}&gl={COUNTRY}&ceid={CEID}"

    feed = feedparser.parse(url)
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
app = FastAPI(title="News API")

@app.get("/today", response_model=List[NewsItem])
def get_today_news():
    return fetch_news()

@app.get("/search", response_model=List[NewsItem])
def search_news(q: str = Query(..., description="Search topic")):
    return fetch_news(query=q)

@app.get("/category/{name}", response_model=List[NewsItem])
def get_by_category(name: str):
    return fetch_news(category=name)
