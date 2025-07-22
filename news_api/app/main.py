from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Tuple
import feedparser
import os
import sys

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Now import from local files
from categories import categories
from utils import calculate_keyword_weight, preprocess_text, generate_smart_label

# -------- CONFIG --------
RSS_BASE = "https://news.google.com/rss"
LANGUAGE = "en"
COUNTRY = "IN"
CEID = f"{COUNTRY}:{LANGUAGE}"

# -------- MODEL --------
class NewsItem(BaseModel):
    category: str
    label: str
    title: str
    link: str
    published: str
    summary: str
    confidence_score: float

# -------- ADVANCED CATEGORIZATION --------
def advanced_categorize_content(title: str, summary: str) -> Tuple[str, float]:
    """Advanced categorization with confidence scoring"""
    
    title_data = preprocess_text(title)
    summary_data = preprocess_text(summary)
    
    category_scores = {}
    
    for category, keywords in categories.items():
        total_score = 0.0
        matched_keywords = []
        
        for keyword in keywords:
            keyword_score = 0.0
            
            # Multi-word phrase matching
            if ' ' in keyword:
                if keyword in title_data['clean_text']:
                    weight = calculate_keyword_weight(keyword, 'title')
                    keyword_score += weight * 2.0
                    matched_keywords.append(f"title:{keyword}")
                    
                if keyword in summary_data['clean_text']:
                    weight = calculate_keyword_weight(keyword, 'summary')
                    keyword_score += weight
                    matched_keywords.append(f"summary:{keyword}")
            else:
                # Single word matching
                if keyword in title_data['word_set']:
                    weight = calculate_keyword_weight(keyword, 'title')
                    freq_multiplier = min(title_data['word_freq'][keyword] * 0.5, 2.0)
                    keyword_score += weight * (1.0 + freq_multiplier)
                    matched_keywords.append(f"title:{keyword}")
                
                if keyword in summary_data['word_set']:
                    weight = calculate_keyword_weight(keyword, 'summary')
                    freq_multiplier = min(summary_data['word_freq'][keyword] * 0.3, 1.5)
                    keyword_score += weight * (1.0 + freq_multiplier)
                    matched_keywords.append(f"summary:{keyword}")
            
            total_score += keyword_score
        
        if total_score > 0:
            # Normalize score
            content_length_factor = min((title_data['text_length'] + summary_data['text_length']) / 50, 1.5)
            keyword_diversity = len(set([match.split(':')[1] for match in matched_keywords]))
            diversity_bonus = min(keyword_diversity * 0.1, 1.0)
            
            normalized_score = total_score * content_length_factor * (1.0 + diversity_bonus)
            category_scores[category] = normalized_score
    
    if not category_scores:
        return "General", 0.0
    
    # Find best category
    best_category = max(category_scores.items(), key=lambda x: x[1])
    best_category_name = best_category[0]
    best_score = best_category[1]
    
    # Calculate confidence
    max_possible_score = len(categories[best_category_name]) * 2.0
    confidence = min(best_score / max_possible_score, 1.0)
    
    # Boost confidence for clear winners
    sorted_scores = sorted(category_scores.values(), reverse=True)
    if len(sorted_scores) > 1:
        score_gap = sorted_scores[0] - sorted_scores[1]
        if score_gap > 2.0:
            confidence = min(confidence * 1.2, 1.0)
    
    return best_category_name, round(confidence, 3)

# -------- SERVICES --------
def build_url(query: Optional[str] = None) -> str:
    if query:
        query = query.replace(" ", "+")
        return f"{RSS_BASE}/search?q={query}&hl={LANGUAGE}-{COUNTRY}&gl={COUNTRY}&ceid={CEID}"
    else:
        return f"{RSS_BASE}?hl={LANGUAGE}-{COUNTRY}&gl={COUNTRY}&ceid={CEID}"

# def fetch_fresh_news(query: Optional[str] = None) -> List[Dict]:
#     """Fetch fresh news - always updated, no cache"""
#     url = build_url(query)
#     feed = feedparser.parse(url)
#     items = []
    
#     for entry in feed.entries:
#         category, confidence = advanced_categorize_content(entry.title, entry.summary)
#         label = generate_smart_label(entry.title)
        
#         items.append({
#             "category": category,
#             "label": label,
#             "title": entry.title,
#             "link": entry.link,
#             "published": entry.published,
#             "summary": entry.summary,
#             "confidence_score": confidence
#         })
    
#     return items

from datetime import datetime

def fetch_fresh_news(query: Optional[str] = None, 
                    limit: int = 15, 
                    min_confidence: float = 0.050) -> List[Dict]:
    """
    Fetch fresh news - always updated, sorted by publish time descending,
    filter by confidence score, return only the top N most recent high-confidence items.
    
    Args:
        query: Search query (optional)
        limit: Maximum number of items to return (default: 15)
        min_confidence: Minimum confidence score threshold (default: 0.050)
    
    Returns:
        List of news items with confidence_score > min_confidence, sorted by publish time
    """
    url = build_url(query)
    feed = feedparser.parse(url)
    temp = []

    for entry in feed.entries:
        # feedparser gives you a struct_time in entry.published_parsed
        published_struct = entry.get('published_parsed')
        if not published_struct:
            # skip if no publish time
            continue

        # convert to a datetime for easy sorting
        published_dt = datetime(*published_struct[:6])

        # categorize & label
        category, confidence = advanced_categorize_content(entry.title, entry.summary)
        label = generate_smart_label(entry.title)

        temp.append({
            "category": category,
            "label": label,
            "title": entry.title,
            "link": entry.link,
            "published": entry.published,
            "summary": entry.summary,
            "confidence_score": confidence,
            "_published_dt": published_dt,  # temporary for sorting
        })

    # sort by datetime descending (latest first)
    temp.sort(key=lambda x: x["_published_dt"], reverse=True)
    
    # filter by confidence score
    high_confidence_items = [item for item in temp if item["confidence_score"] > min_confidence]
    
    # pick top N high-confidence items
    top_filtered = high_confidence_items[:limit]

    # strip out the helper field before returning
    for item in top_filtered:
        del item["_published_dt"]

    return top_filtered


    # sort by datetime descending and pick top 15
    temp.sort(key=lambda x: x["_published_dt"], reverse=True)
    top15 = temp[:15]

    # strip out the helper field before returning
    for item in top15:
        del item["_published_dt"]

    return top15



# -------- APP --------
app = FastAPI(title="Advanced News API - Always Fresh")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=JSONResponse)
def home():
    return {
        "service": "Advanced Google News RSS API - Always Fresh",
        "status": "OK",
        "features": [
            "Advanced categorization",
            "Smart label generation", 
            "Confidence scoring",
            "No caching - always fresh",
            "CORS enabled"
        ],
        "categories": list(categories.keys()),
        "total_categories": len(categories)
    }

@app.get("/today", response_model=List[NewsItem])
def get_today_news(
    limit: int = Query(15, ge=1, le=50, description="Maximum number of news items to return"),
    min_confidence: float = Query(0.080, ge=0.0, le=1.0, description="Minimum confidence score threshold")
):
    """Get today's fresh news with confidence filtering"""
    return fetch_fresh_news(limit=limit, min_confidence=min_confidence)

@app.get("/search", response_model=List[NewsItem])
def search_news(
    q: str = Query(..., description="Search topic"),
    limit: int = Query(15, ge=1, le=50, description="Maximum number of news items to return"),
    min_confidence: float = Query(0.050, ge=0.0, le=1.0, description="Minimum confidence score threshold")
):
    """Search fresh news with confidence filtering"""
    return fetch_fresh_news(query=q, limit=limit, min_confidence=min_confidence)


@app.get("/categories", response_class=JSONResponse)
def get_categories():
    """Get all categories"""
    return {
        "total_categories": len(categories),
        "categories": list(categories.keys())
    }

@app.get("/health", response_class=JSONResponse)
def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "categories_loaded": len(categories),
        "cache_status": "disabled - always fresh"
    }
