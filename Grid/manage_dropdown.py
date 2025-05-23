from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from database.database import get_db
from models.models import DropdownOption, User, MarketingContent
from pydantic import BaseModel, constr
from typing import Annotated
from Currentuser.currentUser import get_current_user

router = APIRouter()

class DropdownToggle(BaseModel):
    column: Annotated[str, constr(strip_whitespace=True, min_length=1)]
    value: Annotated[str, constr(strip_whitespace=True, min_length=1)]
    is_active: bool

@router.post("/dropdown")
def toggle_dropdown(
    data: DropdownToggle,
    db: Session = Depends(get_db),
    Current_user=Depends(get_current_user)
):
    # ✅ Load full user
    user = db.query(User).filter(User.employee_id == Current_user.employee_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # ✅ Check permission
    if not user.permissions or not (user.permissions.get("settings") or user.permissions.get("admin")):
        raise HTTPException(status_code=403, detail="You do not have permission to modify dropdowns.")

    # ✅ Check if column exists in MarketingContent
    valid_columns = MarketingContent.__table__.columns.keys()
    if data.column not in valid_columns:
        raise HTTPException(status_code=400, detail=f"Column '{data.column}' does not exist in marketing_content.")

    # ✅ Normalize
    type_normalized = data.column.lower()
    value_normalized = data.value.lower()

    # ✅ Check existing entry
    existing = db.query(DropdownOption).filter(
        func.lower(DropdownOption.type) == type_normalized,
        func.lower(DropdownOption.value) == value_normalized
    ).first()

    if existing:
        if existing.is_active == data.is_active:
            status = "already active" if data.is_active else "already inactive"
            return {"message": f"Value '{data.value}' is {status}."}
        existing.is_active = data.is_active
        db.commit()
        return {"message": f"Value '{data.value}' has been {'activated' if data.is_active else 'deactivated'}."}

    # ✅ Add new if activating
    if data.is_active:
        new_option = DropdownOption(type=data.column.strip(), value=data.value.strip())
        db.add(new_option)
        db.commit()
        return {"message": f"Value '{data.value}' added and activated."}
    else:
        return {"message": f"Value '{data.value}' does not exist, so cannot deactivate."}
