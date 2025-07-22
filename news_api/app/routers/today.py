from fastapi import APIRouter
from app.services.news_fetcher import fetch_news
from app.models.news import NewsItem
from typing import List

router = APIRouter()

@router.get("/today", response_model=List[NewsItem])
def get_today_news():
    return fetch_news()
