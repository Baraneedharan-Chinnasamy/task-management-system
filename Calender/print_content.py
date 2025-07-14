from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from sqlalchemy.orm import Session
from Currentuser.currentUser import get_current_user
from database.database import get_db
from models.models import MarketingContent, MarketingContentNote

class MarketingContentSummary(BaseModel):
    id: int
    detailed_concept: Optional[str] = None
    format_type: Optional[str] = None
    post_type: Optional[str] = None
    task_name: Optional[str] = None
    created_at: Optional[datetime] = None
    live_date: Optional[date] = None

    class Config:
        orm_mode = True

router = APIRouter()

@router.get("/print-content-notes/")
def get_approved_completed_content(
    brand_name: Optional[str] = Query(None),
    format_type: Optional[str] = Query(None),
    post_type: Optional[str] = Query(None),
    task_name: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("created_at", regex="^(created_at|live_date)$"),
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user)
):

    # Exclude content mapped in notes that are not deleted
    mapped_content_query = db.query(MarketingContentNote.row_id).filter(
        MarketingContentNote.row_id.isnot(None),
        (MarketingContentNote.is_delete == False) | (MarketingContentNote.is_delete.is_(None))
    )

    query = db.query(MarketingContent).filter(
        MarketingContent.status.in_(["Approved","Tasks","Completed"]),
        MarketingContent.is_delete == False,
        ~MarketingContent.id.in_(mapped_content_query)  # Exclude mapped (not soft-deleted) only
    )
    if brand_name:
        query = query.filter(MarketingContent.brand_name == brand_name)
    if format_type:
        query = query.filter(MarketingContent.format_type == format_type)
    if post_type:
        query = query.filter(MarketingContent.post_type == post_type)
    if task_name:
        query = query.filter(MarketingContent.task_name == task_name)

    if sort_by == "created_at":
        query = query.order_by(MarketingContent.created_at.desc())
    elif sort_by == "live_date":
        query = query.order_by(MarketingContent.live_date.desc())

    results = query.all()
    return results

