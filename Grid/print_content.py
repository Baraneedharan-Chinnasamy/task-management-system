from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc
from models.models import MarketingContent
from Grid.input import MarketingContentSchema
from database.database import get_db
from typing import List, Optional

router = APIRouter()

@router.get("/print_content")
def get_paginated_content(
    db: Session = Depends(get_db),
    brand_name: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("created_at"),  # Default: newest first
    sort_order: Optional[str] = Query("desc"),
    offset: int = 0,
    limit: int = 50  # Default to 50 records
):
    query = db.query(MarketingContent).filter(MarketingContent.is_delete == False)

    # Apply filters
    if brand_name:
        query = query.filter(MarketingContent.brand_name.ilike(f"%{brand_name}%"))
    if status:
        query = query.filter(MarketingContent.status == status)

    # Sorting
    sort_fields = {
        "id": MarketingContent.id,
        "brand_name": MarketingContent.brand_name,
        "status": MarketingContent.status,
        "created_at": MarketingContent.created_at,
        "updated_at": MarketingContent.updated_at,
        "live_date": MarketingContent.live_date,
    }
    sort_column = sort_fields.get(sort_by, MarketingContent.id)
    sort_func = desc if sort_order == "desc" else asc
    query = query.order_by(sort_func(sort_column))

    total_records = query.count()

    # Apply pagination
    records = query.offset(offset).limit(limit).all()

    # Determine if there are more records
    has_more = (offset + limit) < total_records

    # Convert SQLAlchemy objects to JSON
    def to_dict(row):
        return {
            "id": row.id,
            "marketing_funnel": row.marketing_funnel,
            "top_pointers": row.top_pointers,
            "post_type": row.post_type,
            "detailed_concept": row.detailed_concept,
            "copy": row.copy,
            "description": row.description,
            "reference": row.reference,
            "media_links": row.media_links,
            "hashtags": row.hashtags,
            "seo_keywords": row.seo_keywords,
            "brand_name": row.brand_name,
            "status": row.status,
            "live_date": row.live_date,
            "task_id": row.task_id,
            "created_by": row.created_by,
            "is_delete": row.is_delete,
            "created_at": row.created_at,
            "updated_at": row.updated_at
        }

    return {
        "data": [to_dict(record) for record in records],
        "pagination": {
            "offset": offset,
            "limit": limit,
            "has_more": has_more,
            "total": total_records
        }
    }
