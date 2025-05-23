from pydantic import BaseModel, EmailStr
from typing import Optional, List

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
    admin: Optional[bool] = False
    brands: Optional[List[str]] = []
    settings: Optional[bool] = False