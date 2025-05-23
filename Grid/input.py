from pydantic import BaseModel
from typing import Optional,List
from datetime import date

class MarketingContentSchema(BaseModel):
    id: Optional[int] = None
    marketing_funnel: Optional[str] = None
    top_pointers: Optional[str] = None
    post_type: Optional[str] = None
    detailed_concept: Optional[str] = None
    copy: Optional[str] = None
    description: Optional[str] = None
    reference: Optional[str] = None
    media_links: Optional[str] = None
    hashtags: Optional[str] = None
    seo_keywords: Optional[str] = None
    brand_name: Optional[str] = None
    status: Optional[str] = "Working"
    live_date: Optional[date] = None
    task_id: Optional[int] = None

    class Config:
        orm_mode = True


