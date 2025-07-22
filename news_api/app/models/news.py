from pydantic import BaseModel

class NewsItem(BaseModel):
    title: str
    link: str
    published: str
    summary: str