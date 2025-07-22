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
    
    # -------- IMPROVED CONFIDENCE CALCULATION (ONLY THIS PART CHANGED) --------
    # Base confidence from score normalization (improved method)
    total_content_words = title_data['text_length'] + summary_data['text_length']
    base_confidence = min(best_score / max(total_content_words * 0.4, 1.0), 1.0)
    
    # Factor 1: Score gap between first and second place (enhanced)
    sorted_scores = sorted(category_scores.values(), reverse=True)
    if len(sorted_scores) > 1:
        score_gap = sorted_scores[0] - sorted_scores[1]
        gap_boost = min(score_gap * 0.15, 0.35)  # Increased boost
        base_confidence += gap_boost
    else:
        # Single category match gets bonus
        base_confidence += 0.2
    
    # Factor 2: Multiple keyword matches bonus
    estimated_matches = min(best_score // 1.5, 10)
    keyword_density_bonus = min(estimated_matches * 0.08, 0.25)
    base_confidence += keyword_density_bonus
    
    # Factor 3: High-value keyword bonus
    high_value_boost = 0.0
    if best_score > 8.0:  # Very strong match
        high_value_boost = 0.25
    elif best_score > 5.0:  # Strong match
        high_value_boost = 0.15
    elif best_score > 3.0:  # Medium match
        high_value_boost = 0.1
    
    # Factor 4: Category-specific confidence multipliers
    category_confidence_multipliers = {
        'Sports': 1.15,     # Sports terms are usually very specific
        'Health': 1.12,     # Medical terms are distinctive
        'Crime': 1.18,      # Legal/crime terms are specific
        'Technology': 1.08, # Tech terms can be broad
        'Politics': 1.1,    # Political terms are fairly specific
        'Business': 1.05    # Business terms can overlap
    }
    
    category_multiplier = category_confidence_multipliers.get(best_category_name, 1.0)
    
    # Calculate final confidence
    final_confidence = min(
        (base_confidence + high_value_boost) * category_multiplier, 
        1.0
    )
    # -------- END OF IMPROVED CONFIDENCE CALCULATION --------
    
    return best_category_name, round(final_confidence, 3)

# -------- SERVICES --------
def build_url(query: Optional[str] = None) -> str:
    if query:
        query = query.replace(" ", "+")
        return f"{RSS_BASE}/search?q={query}&hl={LANGUAGE}-{COUNTRY}&gl={COUNTRY}&ceid={CEID}"
    else:
        return f"{RSS_BASE}?hl={LANGUAGE}-{COUNTRY}&gl={COUNTRY}&ceid={CEID}"

from datetime import datetime

def fetch_fresh_news(query: Optional[str] = None) -> List[Dict]:
    """
    Fetch fresh news - always updated, sorted by publish time descending,
    return only the top 15 most recent items.
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
            "Enhanced confidence scoring",  # Updated this line
            "No caching - always fresh",
            "CORS enabled"
        ],
        "categories": list(categories.keys()),
        "total_categories": len(categories)
    }

@app.get("/today", response_model=List[NewsItem])
def get_today_news():
    """Get today's fresh news"""
    return fetch_fresh_news()

@app.get("/search", response_model=List[NewsItem])
def search_news(q: str = Query(..., description="Search topic")):
    """Search fresh news"""
    return fetch_fresh_news(query=q)

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
        "cache_status": "disabled - always fresh",
        "confidence_system": "enhanced"  # Added this line
    }
