from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    designation: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: str
    otp: str
    new_password: str
    token: str


class PermissionUpdate(BaseModel):
    employee_id: int
    admin: bool
    settings: Optional[bool] = False
    brands: Optional[Dict[str, Dict[str, List[str]]]] = None  # brand -> format -> roles
    reportrix: Optional[List[str]] = []  # List of allowed brands (if using list format)

    class Config:
        extra = "forbid"  # Reject extra fields not defined in the model
