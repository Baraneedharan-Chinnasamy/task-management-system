from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.models import User
from Authentication.inputs import PermissionUpdate
from database.database import get_db
from Currentuser.currentUser import get_current_user

router = APIRouter()

ALLOWED_BRANDS = {"beelittle", "zing", "prathiksham", "adoreaboo"}
ALLOWED_FORMATS = {"Story", "Reels", "Ads", "Post"}
ALLOWED_ROLES = {"creator", "reviewer", "viewer"}

@router.post("/permissions")
def update_user_permissions(
    data: PermissionUpdate,
    db: Session = Depends(get_db),
    Current_user=Depends(get_current_user)
):
    # ✅ Load current user
    requesting_user = db.query(User).filter(User.employee_id == Current_user.employee_id).first()
    if not requesting_user:
        raise HTTPException(status_code=404, detail="Current user not found.")

    # ✅ Only admins can assign permissions
    if not (requesting_user.permissions and requesting_user.permissions.get("admin")):
        raise HTTPException(status_code=403, detail="Only admins can update permissions.")

    # ✅ Load target user
    user = db.query(User).filter(User.employee_id == data.employee_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Target user not found.")

    # ✅ Handle admin = True → grant full access
    if data.admin is True:
        user.permissions = {
            "admin": True,
            "settings": True,
            "brands": {
                brand: {
                    format_type: list(ALLOWED_ROLES)
                    for format_type in ALLOWED_FORMATS
                }
                for brand in ALLOWED_BRANDS
            },
            "reportrix": [brand for brand in ALLOWED_BRANDS]
        }

    # ✅ Handle admin = False (limited access or demotion)
    elif data.admin is False:
        has_settings = bool(data.settings)
        has_brands = bool(data.brands)
        has_reportrix = bool(data.reportrix)

        # ❌ If nothing is provided, remove permissions
        if not has_settings and not has_brands and not has_reportrix:
            user.permissions = None
            db.commit()
            db.refresh(user)
            return {
                "message": f"Permissions removed for user {user.employee_id} (admin revoked).",
                "permissions": None
            }

        # ✅ Validate brand-role-format permissions
        validated_brands = {}
        if has_brands:
            for brand, formats in data.brands.items():
                if brand not in ALLOWED_BRANDS:
                    raise HTTPException(status_code=422, detail=f"Invalid brand: {brand}")
                validated_brands[brand] = {}

                for format_type, roles in formats.items():
                    if format_type not in ALLOWED_FORMATS:
                        raise HTTPException(status_code=422, detail=f"Invalid format: {format_type}")
                    invalid_roles = [r for r in roles if r not in ALLOWED_ROLES]
                    if invalid_roles:
                        raise HTTPException(
                            status_code=422,
                            detail=f"Invalid roles for {brand}/{format_type}: {', '.join(invalid_roles)}"
                        )
                    validated_brands[brand][format_type] = roles

        # ✅ Validate reportrix brand toggles (now it's a list of brands, not a dictionary)
        validated_reportrix = []
        if has_reportrix:
            for brand in data.reportrix:  # Iterate over the list of allowed brands
                if brand not in ALLOWED_BRANDS:
                    raise HTTPException(status_code=422, detail=f"Invalid reportrix brand: {brand}")
                validated_reportrix.append(brand)  # Add brand to the list if allowed


        # ✅ Set permissions
        user.permissions = {
            "admin": False,
            "settings": has_settings,
            "brands": validated_brands if has_brands else {},
            "reportrix": validated_reportrix if validated_reportrix else []
        }


    else:
        raise HTTPException(status_code=422, detail="'admin' must be explicitly true or false.")

    db.commit()
    db.refresh(user)

    return {
        "message": f"Permissions updated for user {user.employee_id}.",
        "permissions": user.permissions
    }
