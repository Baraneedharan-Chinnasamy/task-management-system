from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, func
from models.models import MarketingContent, User, LogMarketingContent
from database.database import get_db
from typing import Optional

router = APIRouter()

@router.get("/print_content")
def get_paginated_content(
    db: Session = Depends(get_db),
    brand_name: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    post_type: Optional[str] = Query(None),
    format_type: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("created_at"),
    sort_order: Optional[str] = Query("desc"),
    offset: int = 0,
    limit: int = 50,
    log_field: Optional[str] = Query(None, description="Optional field to filter logs (case-insensitive, e.g., 'review_comment')")
):
    query = db.query(MarketingContent).filter(MarketingContent.is_delete == False)

    # Apply filters
    if brand_name:
        query = query.filter(MarketingContent.brand_name.ilike(f"%{brand_name}%"))
    if status:
        query = query.filter(MarketingContent.status == status)
    if post_type:
        query = query.filter(MarketingContent.post_type == post_type)
    if format_type:
        query = query.filter(MarketingContent.format_type == format_type)

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
    records = query.offset(offset).limit(limit).all()
    has_more = (offset + limit) < total_records

    # User lookup
    users = db.query(User).all()
    user_map = {u.employee_id: u.username for u in users}

    # Pull logs for the current page of content records
    content_ids = [r.id for r in records]

    log_query = db.query(LogMarketingContent, User).join(User, LogMarketingContent.updated_by == User.employee_id)
    log_query = log_query.filter(LogMarketingContent.row_id.in_(content_ids))

    # If filtering by field name (like review_comment), apply it
    if log_field:
        log_query = log_query.filter(func.lower(LogMarketingContent.field_name) == log_field.lower())
    else:
        # Only include logs for review_comment
        log_query = log_query.filter(LogMarketingContent.field_name == "review_comment")

    logs = log_query.order_by(LogMarketingContent.updated_at.desc()).all()

    # Organize logs by (row_id, field_name)
    log_map = {}
    for log, user in logs:
        key = (log.row_id, log.field_name)
        if key not in log_map:
            log_map[key] = []
        log_map[key].append({
            "value": log.new_value or "",
            "updated_by_name": user.username if user else "Unknown",
            "updated_by": user.employee_id if user else "Unknown",
            "updated_at": log.updated_at.strftime("%Y-%m-%d %H:%M")
        })

    def to_dict(row):
        task_info = {}
        if row.task:
            task_info = {
                "task_name": row.task.task_name,
                "task_status": row.task.status,
                "assigned_to": row.task.assigned_to,
                "assigned_to_name": user_map.get(row.task.assigned_to),
                "due_date": row.task.due_date,
            }

        base = {
            "id": row.id,
            "marketing_funnel": row.marketing_funnel,
            "top_pointers": row.top_pointers,
            "post_type": row.post_type,
            "format_type": row.format_type,
            "detailed_concept": row.detailed_concept,
            "copy": row.copy,
            "reference": row.reference,
            "media_links": row.media_links,
            "brand_name": row.brand_name,
            "status": row.status,
            "review_comment": row.review_comment,
            "review_comment_log": log_map.get((row.id, "review_comment"), []),
            "live_date": row.live_date,
            "task_id": row.task_id,
            "created_by": row.created_by,
            "created_by_name": user_map.get(row.created_by),
            "is_delete": row.is_delete,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            **task_info,
        }

        if row.format_type != "Story":
            base.update({
                "description": row.description,
                "hashtags": row.hashtags,
                "seo_keywords": row.seo_keywords
            })

        if row.format_type == "Ads":
            base["Ads_Type"] = row.Ads_Type

        return base

    return {
        "data": [to_dict(record) for record in records],
        "pagination": {
            "offset": offset,
            "limit": limit,
            "has_more": has_more,
            "total": total_records
        }
    }
