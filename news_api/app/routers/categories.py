from fastapi import APIRouter
from app.services.news_fetcher import fetch_news
from app.models.news import NewsItem
from typing import List

router = APIRouter()

@router.get("/category/{name}", response_model=List[NewsItem])
def get_news_by_category(name: str):
    return fetch_news(category=name)
