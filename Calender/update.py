from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from Currentuser.currentUser import get_current_user
from database.database import get_db
from models.models import MarketingContent, MarketingContentNote

class MarketingContentNoteUpdate(BaseModel):
    row_id: Optional[int] = None
    is_delete: Optional[bool] = None

router = APIRouter()

@router.patch("/update-notes/{note_id}")
def update_marketing_content_note(
    note_id: int,
    update: MarketingContentNoteUpdate,
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user)
):
    note = db.query(MarketingContentNote).filter(MarketingContentNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found.")

    # If updating row_id, check if the marketing content exists
    if update.row_id is not None:
        exists = db.query(MarketingContent.id).filter(MarketingContent.id == update.row_id).first()
        if not exists:
            raise HTTPException(status_code=404, detail="Marketing content row_id does not exist.")
        note.row_id = update.row_id

    if update.is_delete is not None:
        note.is_delete = update.is_delete

    db.commit()
    db.refresh(note)
    return note
