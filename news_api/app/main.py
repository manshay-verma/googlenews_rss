from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import feedparser
import re
import time
import hashlib
from functools import lru_cache
from threading import Lock

# -------- CONFIG --------
RSS_BASE = "https://news.google.com/rss"
LANGUAGE = "en"
COUNTRY = "IN"
CEID = f"{COUNTRY}:{LANGUAGE}"

# Cache settings
CACHE_EXPIRY_SECONDS = 300  # 5 minutes
MAX_CACHE_SIZE = 100  # Maximum cached items

# -------- CACHE SETUP --------
# Time-based cache for API responses
api_cache = {}
cache_lock = Lock()

# -------- CATEGORIES --------
categories = {
    # POLITICS & GOVERNANCE
    "Politics": [
        "government", "election", "parliament", "assembly", "senate", "democracy", "policies", "law", "minister",
        "policy", "constitution", "bill", "cabinet", "diplomacy", "campaign", "politician", "leader", "reform",
        "legislation", "referendum", "coalition", "opposition", "protest", "embassy", "diplomat", "ministry",
        "vote", "voting", "ballot", "candidate", "political", "governance", "administration", "bureaucracy",
        "congress", "legislature", "judicial", "executive", "federal", "state", "local", "municipal", "civic"
    ],
    
    # BUSINESS & ECONOMY
    "Business": [
        "stock", "market", "shares", "bond", "exchange", "economy", "finance", "bank", "investment", "profit",
        "loss", "company", "merger", "acquisition", "startup", "corporation", "trade", "commerce", "export",
        "import", "industry", "revenue", "tax", "dividend", "capital", "funding", "valuation", "earnings",
        "business", "financial", "economic", "commercial", "corporate", "enterprise", "venture", "firm",
        "manufacturing", "retail", "wholesale", "banking", "insurance", "real estate", "equity", "debt"
    ],
    
    # TECHNOLOGY
    "Technology": [
        "software", "hardware", "app", "application", "device", "computer", "artificial intelligence", "machine learning", "cloud",
        "data", "robot", "algorithm", "chip", "processor", "cyber", "security", "startup", "api", "blockchain",
        "internet", "gadget", "innovation", "digital", "virtual reality", "augmented reality", "virtual", "augmented", "network",
        "technology", "tech", "programming", "coding", "development", "smartphone", "tablet", "laptop", "server",
        "database", "platform", "automation", "innovation", "breakthrough", "patent", "research", "scientific"
    ],
    
    # SPORTS
    "Sports": [
        "match", "game", "tournament", "league", "team", "player", "coach", "goal", "score", "athlete",
        "competition", "championship", "finals", "quarterfinal", "semifinal", "medal", "victory", "defeat",
        "stadium", "cricket", "football", "basketball", "olympics", "marathon", "race", "referee",
        "sports", "athletic", "training", "fitness", "exercise", "gym", "workout", "tournament", "trophy",
        "soccer", "tennis", "golf", "baseball", "swimming", "boxing", "wrestling", "hockey", "volleyball"
    ],
    
    # ENTERTAINMENT
    "Entertainment": [
        "movie", "film", "actor", "actress", "director", "drama", "comedy", "trailer", "theater", "musician",
        "music", "concert", "album", "artist", "show", "series", "song", "performance", "celebrity", "stage",
        "festival", "premiere", "blockbuster", "animation", "award", "screenplay", "entertainment", "cinema",
        "television", "tv", "streaming", "netflix", "disney", "hollywood", "bollywood", "dance", "musical"
    ],
    
    # HEALTH & MEDICINE
    "Health": [
        "health", "medical", "medicine", "doctor", "hospital", "patient", "treatment", "therapy", "surgery",
        "disease", "illness", "virus", "bacteria", "infection", "vaccine", "vaccination", "pandemic", "epidemic",
        "healthcare", "pharmaceutical", "drug", "medication", "prescription", "diagnosis", "symptom", "clinic",
        "nurse", "physician", "specialist", "surgeon", "mental health", "psychology", "psychiatry", "wellness",
        "fitness", "nutrition", "diet", "exercise", "obesity", "diabetes", "cancer", "heart", "brain"
    ],
    
    # EDUCATION
    "Education": [
        "education", "school", "university", "college", "student", "teacher", "professor", "academic", "study",
        "research", "learning", "curriculum", "degree", "graduation", "exam", "test", "assessment", "scholarship",
        "tuition", "campus", "classroom", "online learning", "distance education", "e-learning", "training",
        "skill", "knowledge", "literacy", "mathematics", "science", "history", "literature", "language", "arts"
    ],
    
    # ENVIRONMENT & CLIMATE
    "Environment": [
        "environment", "climate", "weather", "global warming", "climate change", "pollution", "carbon", "emission",
        "renewable", "solar", "wind", "hydroelectric", "nuclear", "fossil fuel", "oil", "gas", "coal",
        "recycling", "waste", "conservation", "biodiversity", "ecosystem", "forest", "deforestation", "ocean",
        "wildlife", "endangered", "species", "extinction", "sustainable", "sustainability", "green", "eco"
    ],
    
    # SCIENCE & RESEARCH
    "Science": [
        "science", "research", "study", "experiment", "laboratory", "scientist", "discovery", "breakthrough",
        "physics", "chemistry", "biology", "astronomy", "geology", "mathematics", "engineering", "medicine",
        "technology", "innovation", "theory", "hypothesis", "data", "analysis", "publication", "journal",
        "academic", "university", "institute", "nasa", "space", "mars", "moon", "satellite", "rocket"
    ],
    
    # TRANSPORTATION
    "Transportation": [
        "transport", "transportation", "vehicle", "car", "automobile", "truck", "bus", "train", "railway",
        "airport", "airline", "flight", "plane", "aircraft", "ship", "boat", "metro", "subway", "taxi",
        "uber", "lyft", "ride", "traffic", "road", "highway", "bridge", "tunnel", "parking", "fuel",
        "electric vehicle", "autonomous", "self-driving", "aviation", "maritime", "logistics", "delivery"
    ],
    
    # FOOD & AGRICULTURE
    "Food": [
        "food", "agriculture", "farming", "farmer", "crop", "harvest", "livestock", "cattle", "chicken",
        "restaurant", "chef", "cooking", "recipe", "cuisine", "dish", "meal", "nutrition", "organic",
        "processed", "fast food", "healthy", "diet", "vegetarian", "vegan", "meat", "vegetable", "fruit",
        "grain", "dairy", "milk", "cheese", "bread", "wine", "beer", "beverage", "drink", "coffee", "tea"
    ],
    
    # CRIME & LAW
    "Crime": [
        "crime", "criminal", "police", "arrest", "investigation", "detective", "court", "judge", "lawyer",
        "attorney", "trial", "verdict", "sentence", "prison", "jail", "theft", "robbery", "murder", "assault",
        "fraud", "corruption", "bribery", "law enforcement", "justice", "legal", "lawsuit", "litigation",
        "evidence", "witness", "testimony", "prosecutor", "defense", "guilty", "innocent", "conviction"
    ],
    
    # MILITARY & DEFENSE
    "Military": [
        "military", "army", "navy", "air force", "soldier", "officer", "general", "colonel", "captain",
        "war", "battle", "combat", "weapon", "missile", "bomb", "tank", "aircraft", "ship", "submarine",
        "defense", "security", "national security", "terrorism", "terrorist", "conflict", "peace", "treaty",
        "alliance", "nato", "united nations", "peacekeeping", "veteran", "service", "deployment", "base"
    ],
    
    # REAL ESTATE & CONSTRUCTION
    "Real Estate": [
        "real estate", "property", "house", "home", "apartment", "building", "construction", "developer",
        "architect", "contractor", "mortgage", "loan", "rent", "lease", "tenant", "landlord", "investment",
        "market", "price", "value", "assessment", "inspection", "renovation", "repair", "maintenance",
        "commercial", "residential", "office", "retail", "industrial", "zoning", "permit", "planning"
    ],
    
    # ENERGY & UTILITIES
    "Energy": [
        "energy", "electricity", "power", "utility", "grid", "solar", "wind", "nuclear", "hydroelectric",
        "coal", "oil", "gas", "renewable", "fossil fuel", "carbon", "emission", "green", "sustainable",
        "battery", "storage", "generator", "plant", "station", "transmission", "distribution", "consumption",
        "efficiency", "conservation", "alternative", "biofuel", "geothermal", "tidal", "wave", "hydrogen"
    ],
    
    # FASHION & LIFESTYLE
    "Fashion": [
        "fashion", "style", "clothing", "apparel", "designer", "brand", "luxury", "trend", "collection",
        "runway", "model", "magazine", "beauty", "cosmetics", "makeup", "skincare", "lifestyle", "shopping",
        "retail", "store", "boutique", "mall", "online", "e-commerce", "textile", "fabric", "garment",
        "accessory", "jewelry", "watch", "bag", "shoes", "dress", "suit", "casual", "formal", "seasonal"
    ],
    
    # TRAVEL & TOURISM
    "Travel": [
        "travel", "tourism", "tourist", "vacation", "holiday", "trip", "journey", "destination", "hotel",
        "resort", "accommodation", "booking", "airline", "flight", "airport", "passport", "visa", "cruise",
        "adventure", "sightseeing", "culture", "heritage", "museum", "attraction", "guide", "package",
        "itinerary", "backpacking", "camping", "hiking", "beach", "mountain", "city", "country", "international"
    ],
    
    # RELIGION & SPIRITUALITY
    "Religion": [
        "religion", "religious", "spiritual", "faith", "belief", "worship", "prayer", "church", "temple",
        "mosque", "synagogue", "cathedral", "priest", "pastor", "imam", "rabbi", "monk", "nun", "clergy",
        "christian", "islam", "hindu", "buddhist", "jewish", "sikh", "scripture", "bible", "quran", "holy",
        "sacred", "divine", "god", "allah", "ceremony", "ritual", "pilgrimage", "festival", "celebration"
    ],
    
    # ARTS & CULTURE
    "Arts": [
        "art", "artist", "painting", "sculpture", "gallery", "museum", "exhibition", "culture", "cultural",
        "heritage", "tradition", "literature", "poetry", "novel", "book", "author", "writer", "publisher",
        "theater", "drama", "opera", "dance", "ballet", "photography", "craft", "design", "creative",
        "aesthetic", "masterpiece", "collection", "antique", "artifact", "history", "historical", "archive"
    ],
    
    # SOCIAL ISSUES
    "Social Issues": [
        "social", "society", "community", "activist", "protest", "demonstration", "rights", "human rights",
        "civil rights", "equality", "discrimination", "racism", "sexism", "gender", "minority", "majority",
        "poverty", "homeless", "unemployment", "welfare", "charity", "nonprofit", "volunteer", "donation",
        "justice", "injustice", "reform", "change", "movement", "campaign", "advocacy", "awareness", "support"
    ],
    
    # INTERNATIONAL RELATIONS
    "International": [
        "international", "global", "world", "diplomatic", "embassy", "ambassador", "foreign", "relations",
        "treaty", "agreement", "alliance", "partnership", "cooperation", "conflict", "resolution", "peace",
        "war", "sanctions", "trade", "export", "import", "summit", "conference", "organization", "united nations",
        "european union", "nato", "g7", "g20", "bilateral", "multilateral", "regional", "continental", "border"
    ],
    
    # WEATHER & DISASTERS
    "Weather": [
        "weather", "climate", "temperature", "rain", "snow", "storm", "hurricane", "tornado", "cyclone",
        "flood", "drought", "earthquake", "tsunami", "volcano", "wildfire", "disaster", "natural disaster",
        "emergency", "evacuation", "rescue", "relief", "damage", "destruction", "recovery", "rebuild",
        "forecast", "prediction", "warning", "alert", "meteorology", "atmospheric", "seasonal", "extreme"
    ],
    
    # FAMILY & RELATIONSHIPS
    "Family": [
        "family", "parent", "mother", "father", "child", "baby", "pregnancy", "birth", "adoption", "marriage",
        "wedding", "divorce", "relationship", "couple", "partner", "dating", "love", "romance", "friendship",
        "community", "neighborhood", "home", "household", "domestic", "parenting", "childcare", "education",
        "support", "care", "elderly", "senior", "retirement", "generation", "tradition", "culture", "values"
    ],
    
    # COMMUNICATION & MEDIA
    "Media": [
        "media", "news", "newspaper", "magazine", "television", "radio", "broadcast", "journalism", "reporter",
        "journalist", "editor", "publisher", "communication", "social media", "facebook", "twitter", "instagram",
        "youtube", "linkedin", "internet", "website", "blog", "podcast", "streaming", "digital", "online",
        "platform", "content", "information", "data", "privacy", "freedom", "press", "censorship", "publication"
    ],
    
    # AEROSPACE & AVIATION
    "Aerospace": [
        "aerospace", "aviation", "aircraft", "airplane", "helicopter", "drone", "pilot", "flight", "airport",
        "airline", "aviation", "space", "spacecraft", "satellite", "rocket", "launch", "mission", "nasa",
        "astronaut", "space station", "mars", "moon", "planet", "universe", "galaxy", "telescope", "observatory",
        "exploration", "discovery", "research", "technology", "engineering", "manufacturing", "commercial", "military"
    ],
    
    # MANUFACTURING & INDUSTRY
    "Manufacturing": [
        "manufacturing", "industry", "industrial", "factory", "plant", "production", "assembly", "automation",
        "machinery", "equipment", "supply chain", "logistics", "quality", "safety", "worker", "labor",
        "union", "employment", "job", "career", "skill", "training", "certification", "standard", "regulation",
        "compliance", "inspection", "maintenance", "repair", "upgrade", "innovation", "efficiency", "productivity"
    ],
    
    # RETAIL & CONSUMER
    "Retail": [
        "retail", "shopping", "store", "mall", "supermarket", "grocery", "consumer", "customer", "service",
        "sale", "discount", "promotion", "brand", "product", "merchandise", "inventory", "supply", "demand",
        "market", "competition", "price", "value", "quality", "satisfaction", "loyalty", "experience",
        "e-commerce", "online", "delivery", "shipping", "return", "exchange", "warranty", "guarantee"
    ],
    
    # AGRICULTURE & FARMING
    "Agriculture": [
        "agriculture", "farming", "farm", "farmer", "crop", "harvest", "planting", "seed", "soil", "irrigation",
        "livestock", "cattle", "dairy", "poultry", "organic", "pesticide", "fertilizer", "sustainable",
        "greenhouse", "hydroponics", "biotechnology", "genetic", "modification", "food security", "nutrition",
        "export", "import", "market", "price", "subsidy", "policy", "regulation", "cooperative", "rural"
    ],
    
    # AUTOMOTIVE
    "Automotive": [
        "automotive", "car", "vehicle", "automobile", "truck", "motorcycle", "electric", "hybrid", "fuel",
        "engine", "manufacturing", "dealer", "sales", "repair", "maintenance", "parts", "accessory",
        "driving", "license", "insurance", "accident", "safety", "crash", "test", "regulation", "emission",
        "pollution", "technology", "innovation", "autonomous", "self-driving", "smart", "connected", "mobility"
    ],
    
    # TELECOMMUNICATIONS
    "Telecommunications": [
        "telecommunications", "telecom", "phone", "mobile", "smartphone", "cellular", "network", "internet",
        "broadband", "wireless", "cable", "satellite", "fiber", "5g", "4g", "data", "service", "provider",
        "operator", "communication", "technology", "infrastructure", "tower", "antenna", "signal", "coverage",
        "roaming", "plan", "subscription", "billing", "customer", "support", "repair", "upgrade", "innovation"
    ],
    
    # HOSPITALITY & TOURISM
    "Hospitality": [
        "hospitality", "hotel", "resort", "accommodation", "guest", "service", "restaurant", "food", "beverage",
        "tourism", "travel", "vacation", "holiday", "booking", "reservation", "check-in", "check-out",
        "staff", "management", "quality", "rating", "review", "experience", "luxury", "budget", "amenity",
        "facility", "room", "suite", "conference", "event", "wedding", "catering", "entertainment", "recreation"
    ],
    
    # FINANCE & BANKING
    "Finance": [
        "finance", "financial", "bank", "banking", "loan", "credit", "debt", "investment", "savings", "account",
        "interest", "rate", "mortgage", "insurance", "pension", "retirement", "fund", "portfolio", "stock",
        "bond", "mutual fund", "exchange", "market", "trading", "broker", "advisor", "planning", "budget",
        "tax", "audit", "accounting", "payroll", "transaction", "payment", "currency", "exchange", "inflation"
    ],
    
    # LOGISTICS & SUPPLY CHAIN
    "Logistics": [
        "logistics", "supply chain", "transportation", "shipping", "delivery", "freight", "cargo", "warehouse",
        "distribution", "inventory", "storage", "packaging", "handling", "loading", "unloading", "tracking",
        "route", "optimization", "efficiency", "cost", "time", "schedule", "planning", "coordination",
        "management", "system", "technology", "automation", "robot", "drone", "truck", "rail", "air", "sea"
    ]
}

# -------- MODEL --------
class NewsItem(BaseModel):
    category: str
    label: str
    title: str
    link: str
    published: str
    summary: str

# -------- LRU CACHED FUNCTIONS --------
@lru_cache(maxsize=1000)  # Cache for category analysis
def categorize_content_cached(title: str, summary: str) -> str:
    """LRU cached version of category analysis"""
    text = f"{title} {summary}".lower()
    for category, keywords in categories.items():
        if any(keyword in text for keyword in keywords):
            return category
    return "General"

@lru_cache(maxsize=500)   # Cache for label generation
def generate_label_cached(title: str) -> str:
    """LRU cached version of label generation"""
    # Remove common stop words but keep important ones
    stop_words = {
        'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 
        'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
        'to', 'was', 'were', 'will', 'with', 'says', 'said', 'after'
    }
    
    # Clean and split title
    title_clean = re.sub(r'[^\w\s]', '', title.lower())
    words = title_clean.split()
    
    # Remove stop words and keep important words
    important_words = [word for word in words if word not in stop_words and len(word) > 2]
    
    # Take first 4-5 most important words
    label_words = important_words[:5]
    
    # If we have less than 3 words, include some stop words back
    if len(label_words) < 3:
        all_words = [word for word in words if len(word) > 2]
        label_words = all_words[:4]
    
    # Create label
    label = ' '.join(label_words).title()
    
    # If still empty, use first few words of original title
    if not label.strip():
        label = ' '.join(title.split()[:4]).title()
    
    return label

# -------- CACHE UTILITIES --------
def generate_cache_key(query: Optional[str] = None) -> str:
    """Generate a cache key based on query parameters"""
    key_string = f"query:{query or 'today'}"
    return hashlib.md5(key_string.encode()).hexdigest()

def get_from_cache(cache_key: str):
    """Get data from time-based cache if not expired"""
    with cache_lock:
        cached_data = api_cache.get(cache_key)
        if cached_data:
            timestamp, data = cached_data
            if time.time() - timestamp < CACHE_EXPIRY_SECONDS:
                return data
            else:
                # Remove expired data
                del api_cache[cache_key]
    return None

def store_in_cache(cache_key: str, data):
    """Store data in time-based cache with cleanup"""
    with cache_lock:
        # Clean up old entries if cache is getting too large
        if len(api_cache) >= MAX_CACHE_SIZE:
            current_time = time.time()
            expired_keys = [
                key for key, (timestamp, _) in api_cache.items()
                if current_time - timestamp >= CACHE_EXPIRY_SECONDS
            ]
            for key in expired_keys:
                del api_cache[key]
            
            # If still too large, remove oldest entries
            if len(api_cache) >= MAX_CACHE_SIZE:
                sorted_items = sorted(api_cache.items(), key=lambda x: x[1][0])
                for key, _ in sorted_items[:MAX_CACHE_SIZE // 4]:  # Remove 25%
                    del api_cache[key]
        
        api_cache[cache_key] = (time.time(), data)

# -------- SERVICES --------
def build_url(query: Optional[str] = None) -> str:
    if query:
        query = query.replace(" ", "+")
        return f"{RSS_BASE}/search?q={query}&hl={LANGUAGE}-{COUNTRY}&gl={COUNTRY}&ceid={CEID}"
    else:
        return f"{RSS_BASE}?hl={LANGUAGE}-{COUNTRY}&gl={COUNTRY}&ceid={CEID}"

def fetch_news_from_rss(query: Optional[str] = None):
    """Fetch fresh news from RSS feed"""
    url = build_url(query)
    feed = feedparser.parse(url)
    items = []
    
    for entry in feed.entries:
        # Use LRU cached functions
        category = categorize_content_cached(entry.title, entry.summary)
        label = generate_label_cached(entry.title)
        
        items.append({
            "category": category,
            "label": label,
            "title": entry.title,
            "link": entry.link,
            "published": entry.published,
            "summary": entry.summary
        })
    
    return items

def fetch_news(query: Optional[str] = None):
    """Main function with time-based caching"""
    cache_key = generate_cache_key(query)
    
    # Try to get from cache first
    cached_data = get_from_cache(cache_key)
    if cached_data:
        return cached_data
    
    try:
        # Fetch fresh data
        fresh_data = fetch_news_from_rss(query)
        
        # Store in cache
        store_in_cache(cache_key, fresh_data)
        
        return fresh_data
    
    except Exception as e:
        # If fresh fetch fails, try to return stale cache data
        with cache_lock:
            cached_data = api_cache.get(cache_key)
            if cached_data:
                return cached_data[1]  # Return data even if expired
        
        # If no cache available, return empty list
        return []

# -------- CACHE MANAGEMENT ENDPOINTS --------
@lru_cache(maxsize=1)
def get_cache_stats():
    """Get cache statistics"""
    with cache_lock:
        current_time = time.time()
        active_entries = sum(1 for timestamp, _ in api_cache.values() 
                           if current_time - timestamp < CACHE_EXPIRY_SECONDS)
        return {
            "total_entries": len(api_cache),
            "active_entries": active_entries,
            "expired_entries": len(api_cache) - active_entries,
            "lru_categorize_info": categorize_content_cached.cache_info()._asdict(),
            "lru_label_info": generate_label_cached.cache_info()._asdict()
        }

# -------- APP --------
app = FastAPI(title="News API with Cache & LRU")

@app.get("/", response_class=JSONResponse)
def home():
    return {
        "service": "Google News RSS FastAPI with Cache & LRU",
        "status": "OK",
        "features": [
            "Auto-categorization", 
            "Label generation", 
            "Time-based caching", 
            "LRU caching",
            "Search", 
            "Today's news"
        ],
        "cache_expiry_seconds": CACHE_EXPIRY_SECONDS,
        "max_cache_size": MAX_CACHE_SIZE
    }

@app.get("/today", response_model=List[NewsItem])
def get_today_news():
    """Get today's news (cached for 5 minutes)"""
    return fetch_news()

@app.get("/search", response_model=List[NewsItem])
def search_news(q: str = Query(..., description="Search topic")):
    """Search news (cached for 5 minutes per query)"""
    return fetch_news(query=q)

@app.get("/cache/stats", response_class=JSONResponse)
def get_cache_statistics():
    """Get cache performance statistics"""
    # Clear the cache for this function to get fresh stats
    get_cache_stats.cache_clear()
    return get_cache_stats()

@app.post("/cache/clear", response_class=JSONResponse)
def clear_cache():
    """Clear all caches"""
    with cache_lock:
        api_cache.clear()
    
    categorize_content_cached.cache_clear()
    generate_label_cached.cache_clear()
    get_cache_stats.cache_clear()
    
    return {
        "message": "All caches cleared successfully",
        "timestamp": time.time()
    }
