from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from models.models import MarketingContent, DropdownOption
from Grid.input import MarketingContentSchema
from database.database import get_db
from Currentuser.currentUser import get_current_user

router = APIRouter()

def is_dropdown_enabled(db: Session, field: str) -> bool:
    return db.query(DropdownOption).filter(
        func.lower(DropdownOption.type) == field.lower(),
        DropdownOption.is_active == True
    ).first() is not None

def validate_dropdown_value(db: Session, field: str, value: str):
    if not value:
        return
    if not is_dropdown_enabled(db, field):
        return  # Free-text mode, skip validation

    exists = db.query(DropdownOption).filter(
        func.lower(DropdownOption.type) == field.lower(),
        func.lower(DropdownOption.value) == value.lower(),
        DropdownOption.is_active == True
    ).first()

    if not exists:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid or inactive value '{value}' for '{field}'"
        )

@router.post("/upsert_content")
def upsert_content(
    data: MarketingContentSchema,
    db: Session = Depends(get_db),
    Current_user=Depends(get_current_user)
):
    if not Current_user or not hasattr(Current_user, "employee_id"):
        raise HTTPException(status_code=401, detail="Unauthorized: user not found")

    try:
        # Loop through all string fields in the model
        for field, value in data.model_dump(exclude_unset=True).items():
            if isinstance(value, str):
                validate_dropdown_value(db, field, value)

        if data.id:
            content = db.query(MarketingContent).filter_by(id=data.id, is_delete=False).first()
            if not content:
                raise HTTPException(status_code=404, detail="Content not found")
            for field, value in data.model_dump(exclude_unset=True).items():
                if value is not None:
                    setattr(content, field, value)
        else:
            new_data = data.model_dump(exclude_unset=True)
            new_data["created_by"] = Current_user.employee_id
            content = MarketingContent(**new_data)
            db.add(content)

        db.commit()
        db.refresh(content)
        return content

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print("❌ Error:", str(e))
        raise HTTPException(status_code=500, detail="Internal Server Error")
