from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from models.models import User, DropdownOption
from Authentication.inputs import PermissionUpdate
from database.database import get_db
from Currentuser.currentUser import get_current_user

router = APIRouter()

@router.post("/permissions")
def update_user_permissions(
    data: PermissionUpdate,
    db: Session = Depends(get_db),
    Current_user: User = Depends(get_current_user)
):
    # ✅ Only allow admins to update permissions
    if not Current_user.permissions or not Current_user.permissions.get("admin", False):
        raise HTTPException(status_code=403, detail="Only admins can update permissions.")

    # ✅ Fetch the user to be updated
    user = db.query(User).filter(User.employee_id == data.employee_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # ✅ Start with current permissions or default
    updated_permissions = user.permissions or {"admin": False}

    # ✅ If admin is True, override all
    if data.admin is True:
        user.permissions = {"admin": True}
    else:
        # ✅ Validate brands if provided
        if data.brands is not None:
            valid_brands = db.query(DropdownOption.value).filter(
                func.lower(DropdownOption.type) == "brand_name",
                DropdownOption.is_active == True
            ).all()
            valid_brand_list = {b[0].lower() for b in valid_brands}
            requested_brands = {b.lower() for b in data.brands}

            invalid = requested_brands - valid_brand_list
            if invalid:
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid or inactive brand(s): {', '.join(invalid)}"
                )

            updated_permissions["brands"] = data.brands

        # ✅ Set settings permission if provided
        if data.settings is not None:
            updated_permissions["settings"] = data.settings

        # ✅ Ensure admin is explicitly False if not True
        updated_permissions["admin"] = False
        user.permissions = updated_permissions

    db.commit()
    return {
        "message": f"Permissions updated for user {user.employee_id}.",
        "permissions": user.permissions
    }
