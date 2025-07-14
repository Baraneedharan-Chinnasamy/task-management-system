from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from Currentuser.currentUser import get_current_user
from database.database import get_db
from models.models import DropdownOption, MarketingContent, MarketingContentNote
from datetime import date

class MarketingContentNoteCreate(BaseModel):
    type: str
    notes: str
    date: date


router = APIRouter()

@router.post("/Create-notes")
def create_marketing_content_note(
    note: MarketingContentNoteCreate, 
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user)
):
    # Validate type
    valid_types = db.query(DropdownOption.value).filter(
        DropdownOption.type == "format_type",
        DropdownOption.is_active == True
    ).all()
    valid_types = [v[0] for v in valid_types]

    if note.type not in valid_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid type. Allowed types: {valid_types}"
        )

    # Create note (row_id and is_delete are not set here)
    new_note = MarketingContentNote(
        type=note.type,
        notes=note.notes,
        date=note.date,
        created_by=current_user.employee_id
    )
    db.add(new_note)
    db.commit()
    db.refresh(new_note)

    return new_note
