import feedparser
from app.config import RSS_BASE, DEFAULT_LANGUAGE, DEFAULT_COUNTRY, CEID

def fetch_news(query=None, category=None):
    if query:
        query = query.replace(" ", "+")
        url = f"{RSS_BASE}/search?q={query}&hl={DEFAULT_LANGUAGE}-{DEFAULT_COUNTRY}&gl={DEFAULT_COUNTRY}&ceid={CEID}"
    elif category:
        url = f"{RSS_BASE}/headlines/section/topic/{category.upper()}?hl={DEFAULT_LANGUAGE}-{DEFAULT_COUNTRY}&gl={DEFAULT_COUNTRY}&ceid={CEID}"
    else:
        url = f"{RSS_BASE}?hl={DEFAULT_LANGUAGE}-{DEFAULT_COUNTRY}&gl={DEFAULT_COUNTRY}&ceid={CEID}"

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


