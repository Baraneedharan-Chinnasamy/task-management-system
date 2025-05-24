from pydantic import BaseModel
from typing import Optional
from datetime import date

class MarketingContentSchema(BaseModel):
    id: Optional[int] = None
    marketing_funnel: Optional[str] = None
    top_pointers: Optional[str] = None
    post_type: Optional[str] = None
    format_type: Optional[str] = None  
    Ads_Type: Optional[str] = None     
    detailed_concept: Optional[str] = None
    copy: Optional[str] = None
    description: Optional[str] = None
    reference: Optional[str] = None
    media_links: Optional[str] = None
    hashtags: Optional[str] = None
    seo_keywords: Optional[str] = None
    brand_name: Optional[str] = None
    status: Optional[str] = "Working"
    review_comment: Optional[str] = None
    live_date: Optional[date] = None
    task_id: Optional[int] = None
    is_delete: Optional[bool] = False

    class Config:
        from_attributes = True
