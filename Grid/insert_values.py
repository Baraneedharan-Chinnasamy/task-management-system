from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from Logs.functions import log_marketing_field_change
from models.models import MarketingContent, DropdownOption, User
from Grid.input import MarketingContentSchema
from database.database import get_db
from Currentuser.currentUser import get_current_user
from datetime import datetime

router = APIRouter()


# Utility: check if dropdown validation is needed
def is_dropdown_enabled(db: Session, field: str) -> bool:
    return db.query(DropdownOption).filter(
        func.lower(DropdownOption.type) == field.lower(),
        DropdownOption.is_active == True
    ).first() is not None


# Utility: validate value against dropdown options
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


# Utility: generate a unique task name
def generate_task_name(db: Session, brand_name: str, post_type: str, format_type: str) -> str:
    now = datetime.now()
    date_segment = now.strftime("%y%m")  # e.g., "2506"
    prefix = f"{brand_name[:3].upper()}-{post_type}-{format_type}-{date_segment}"

    existing = (
        db.query(MarketingContent.task_name)
        .filter(MarketingContent.task_name.like(f"{prefix}-%"))
        .order_by(MarketingContent.task_name.desc())
        .first()
    )

    if existing and existing[0]:
        try:
            last_seq = int(existing[0].split("-")[-1])
            next_seq = last_seq + 1
        except ValueError:
            next_seq = 1
    else:
        next_seq = 1

    return f"{prefix}-{str(next_seq).zfill(4)}"


# Main route: upsert content
@router.post("/upsert_content")
def upsert_content(
    data: MarketingContentSchema,
    db: Session = Depends(get_db),
    Current_user=Depends(get_current_user)
):
    if not Current_user or not hasattr(Current_user, "employee_id"):
        raise HTTPException(status_code=401, detail="Unauthorized: user not found")

    try:
        updated_fields = {}
        is_update = bool(data.id)
        content = None

        # Validate dropdown values
        for field, value in data.model_dump(exclude_unset=True).items():
            if isinstance(value, str):
                validate_dropdown_value(db, field, value)

        if is_update:
            content = db.query(MarketingContent).filter_by(id=data.id).first()
            if not content:
                raise HTTPException(status_code=404, detail="Content not found")

            for field, value in data.model_dump(exclude_unset=True).items():
                current_value = getattr(content, field)
                if value is not None and value != current_value:
                    setattr(content, field, value)
                    updated_fields[field] = value
                    if field in ["status", "review_comment"]:
                        log_marketing_field_change(
                            db=db,
                            row_id=content.id,
                            field_name=field,
                            old_value=current_value,
                            new_value=value,
                            user_id=Current_user.employee_id
                        )
        else:
            new_data = data.model_dump(exclude_unset=True)
            new_data["created_by"] = Current_user.employee_id
            content = MarketingContent(**new_data)
            db.add(content)
            updated_fields = new_data  # All fields are new

        # Task name generation logic (only once on first approval)
        if content.status and content.status.lower() == "approved" and not content.task_name:
            if not content.brand_name or not content.post_type or not content.format_type:
                raise HTTPException(
                    status_code=422,
                    detail="Cannot generate task name: 'brand_name', 'post_type', and 'format_type' must be filled."
                )
            generated_name = generate_task_name(db, content.brand_name, content.post_type, content.format_type)
            content.task_name = generated_name
            updated_fields["task_name"] = generated_name

        db.commit()
        db.refresh(content)
        user = db.query(User).filter(User.employee_id == content.created_by).first()
        # Base response
        response = {
            "id": content.id,
            **updated_fields,
            "created_by": content.created_by,
            "created_by_name": Current_user.username if Current_user else None,
        }

        # Add only the relevant timestamp
        if data.id:
            response["updated_at"] = content.updated_at
        else:
            response["created_at"] = content.created_at
        # Always return id + updated fields
        return response

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print("❌ Error:", str(e))
        raise HTTPException(status_code=500, detail="Internal Server Error")
