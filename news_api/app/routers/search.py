from fastapi import APIRouter, Query
from app.services.news_fetcher import fetch_news
from app.models.news import NewsItem
from typing import List

router = APIRouter()

@router.get("/search", response_model=List[NewsItem])
def search_news(q: str = Query(..., description="Search query")):
    return fetch_news(query=q)
