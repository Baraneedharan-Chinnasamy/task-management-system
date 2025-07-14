from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import and_
from collections import defaultdict
from Currentuser.currentUser import get_current_user
from database.database import get_db
from models.models import MarketingContentNote
from sqlalchemy.orm import Session
from collections import defaultdict

class TaskInfo(BaseModel):
    task_id: int
    task_name: Optional[str]
    status: Optional[str]

    class Config:
        orm_mode = True

class MarketingContentInfo(BaseModel):
    id: int
    status: Optional[str]
    task: Optional[TaskInfo]

    class Config:
        orm_mode = True

class MarketingContentNoteOut(BaseModel):
    id: int
    type: str
    notes: str
    date: date
    row_id: Optional[int] = None
    marketing_content: Optional[MarketingContentInfo] = None

    class Config:
        orm_mode = True

class NotesByDate(BaseModel):
    date: date
    notes: List[MarketingContentNoteOut]



router = APIRouter()

@router.get("/print-notes", response_model=List[NotesByDate])
def get_notes_by_date(
    date: Optional[date] = Query(None, description="Single date (YYYY-MM-DD)"),
    start_date: Optional[date] = Query(None, description="Range start date"),
    end_date: Optional[date] = Query(None, description="Range end date"),
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user)
):
    query = db.query(MarketingContentNote).filter(
        (MarketingContentNote.is_delete == False) | (MarketingContentNote.is_delete.is_(None))
    )

    if date:
        query = query.filter(MarketingContentNote.date == date)
    elif start_date and end_date:
        query = query.filter(
            MarketingContentNote.date >= start_date,
            MarketingContentNote.date <= end_date
        )
    else:
        raise HTTPException(status_code=400, detail="You must provide either 'date' or both 'start_date' and 'end_date'.")

    notes = query.all()

    grouped = defaultdict(list)
    for note in notes:
        # Prepare marketing_content info if row_id is not None
        marketing_content_info = None
        if note.row_id is not None and note.marketing_content is not None:
            mc = note.marketing_content
            # Prepare task info if task_id is present and task exists
            task_info = None
            if mc.task_id and mc.task is not None:
                task_info = TaskInfo(
                    task_id=mc.task.task_id,
                    task_name=mc.task.task_name,
                    status=mc.task.status.value if hasattr(mc.task.status, "value") else mc.task.status
                )
            marketing_content_info = MarketingContentInfo(
                id=mc.id,
                status=mc.status,
                task=task_info
            )

        grouped[note.date].append(
            MarketingContentNoteOut(
                id=note.id,
                type=note.type,
                notes=note.notes,
                date=note.date,
                row_id=note.row_id,
                marketing_content=marketing_content_info
            )
        )

    result = [
        NotesByDate(
            date=day,
            notes=day_notes
        )
        for day, day_notes in sorted(grouped.items())
    ]
    return result
