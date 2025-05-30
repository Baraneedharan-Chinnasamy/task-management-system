from fastapi import APIRouter, Depends, HTTPException, Response, Query
from sqlalchemy.orm import Session
from models.models import User,DropdownOption
from Authentication.functions import hash_password, verify_password, create_access_token, decode_token,send_email
from Authentication.inputs import UserCreate, ForgotPasswordRequest, ResetPasswordRequest
from database.database import get_db
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import timedelta
import logging
import random
from fastapi.responses import JSONResponse
from Currentuser.currentUser import get_current_user
from logger.logger import get_logger

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

@router.post("/signup")
def signup(user: UserCreate, db: Session = Depends(get_db)):
    logger = get_logger("auth", "auth.log")
    logger.info(f"Signup attempt for username='{user.username}', email='{user.email}'")

    existing = db.query(User).filter((User.username == user.username) | (User.email == user.email)).first()
    if existing:
        logger.warning(f"Signup failed: Username or email already exists - {user.username} / {user.email}")
        raise HTTPException(status_code=400, detail="Username or email already exists")

    new_user = User(
        username=user.username,
        email=user.email,
        password_hash=hash_password(user.password),
        designation=user.designation
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    logger.info(f"New user created: user_id={new_user.employee_id}, username={new_user.username}")
    return {"message": "User created successfully"}


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    logger = get_logger("auth", "auth.log")
    logger.info(f"Login attempt for username='{form_data.username}'")

    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        logger.warning(f"Login failed for username='{form_data.username}'")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user.username, "employee_id": user.employee_id})
    logger.info(f"Login successful for user_id={user.employee_id}, username={user.username}")

    response = JSONResponse(content={"message": "Login successful"})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=60 * 60 * 24 * 7,
        expires=60 * 60 * 24 * 7,
        secure=False
    )
    return response


@router.post("/forgot-password")
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    logger = get_logger("auth", "auth.log")
    logger.info(f"Password reset requested for email='{request.email}'")

    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        logger.warning(f"Password reset failed: email not found - {request.email}")
        raise HTTPException(status_code=404, detail="Email not found")

    otp = str(random.randint(100000, 999999))
    payload = {"sub": user.email, "otp": otp}
    token = create_access_token(payload, expires_delta=timedelta(minutes=10))

    email_body = f"Hi {user.username},\n\nYour OTP for password reset is: {otp}\n\nThis OTP is valid for 10 minutes."
    send_email(user.email, "Your OTP for Password Reset", email_body)
    logger.info(f"OTP sent to email={user.email}, OTP={otp} (masked in logs)")

    return {"message": "OTP has been sent to your email", "token": token}


@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    logger = get_logger("auth", "auth.log")
    logger.info(f"Reset password attempt for email='{data.email}'")

    payload = decode_token(data.token)
    if not payload:
        logger.warning("Invalid or expired reset token")
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    email = payload.get("sub")
    token_otp = payload.get("otp")

    if email != data.email or token_otp != data.otp:
        logger.warning("Reset password failed: email or OTP mismatch")
        raise HTTPException(status_code=400, detail="Invalid email or OTP")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        logger.warning("Reset password failed: user not found")
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = hash_password(data.new_password)
    db.commit()
    logger.info(f"Password reset successful for user_id={user.employee_id}, email={user.email}")
    return {"message": "Password reset successful"}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(
        key="access_token",
        path="/",         
        httponly=True,    
        samesite="lax"    
    )
    return {"message": "Logged out"}


@router.get("/me")
def get_me(token: str = Depends(oauth2_scheme)):
    return {"message": "You're authenticated", "token": token}



@router.get("/users")
def read_current_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logger = get_logger("auth", "auth.log")
    logger.info(f"Fetching all users for user_id={current_user.employee_id}")

    # ✅ Fetch all users
    all_users = db.query(User).all()
    people = [
        {
            "employee_id": user.employee_id,
            "username": user.username
        }
        for user in all_users
    ]

    # ✅ Fetch all active dropdown options
    active_options = db.query(DropdownOption.type, DropdownOption.value).filter(
        DropdownOption.is_active == True
    ).all()

    dropdown_map_full = {}
    for type_, value in active_options:
        type_lower = type_.lower()
        dropdown_map_full.setdefault(type_lower, []).append(value)

    # ✅ Filter dropdowns based on current user's permissions
    filtered_dropdown_map = {}

    user_permissions = current_user.permissions or {}
    allowed_brands = user_permissions.get("brands", {})

    # ✅ Filter brands
    filtered_dropdown_map["brand_name"] = [
        brand for brand in dropdown_map_full.get("brand_name", [])
        if brand in allowed_brands
    ] if allowed_brands else []

    # ✅ Filter roles and format_types
    allowed_roles = set()
    allowed_formats = set()

    for brand_perms in allowed_brands.values():
        for format_type, roles in brand_perms.items():
            allowed_formats.add(format_type)
            allowed_roles.update(roles)

    # ✅ Filter roles
    filtered_dropdown_map["role"] = [
        role for role in dropdown_map_full.get("role", [])
        if role in allowed_roles
    ]

    # ✅ Filter format_type
    filtered_dropdown_map["format_type"] = [
        fmt for fmt in dropdown_map_full.get("format_type", [])
        if fmt in allowed_formats
    ]

    # ✅ Copy other dropdowns without filtering
    for key in dropdown_map_full:
        if key not in {"brand_name", "role", "format_type"}:
            filtered_dropdown_map[key] = dropdown_map_full[key]

    logger.debug(f"{len(people)} users fetched by user_id={current_user.employee_id}")
    logger.debug(f"Filtered dropdowns: {filtered_dropdown_map}")

    return {
        "employee_id": current_user.employee_id,
        "username": current_user.username,
        "email": current_user.email,
        "designation": current_user.designation,
        "permissions": current_user.permissions,
        "people": people,
        "dropdowns": filtered_dropdown_map
    }
