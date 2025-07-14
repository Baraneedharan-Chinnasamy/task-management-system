# import datetime
# from fastapi import APIRouter, Depends, HTTPException, Query
# from sqlalchemy.orm import Session
# from models.models import User
# from Authentication.functions import hash_password, create_access_token, decode_token, send_email
# from Authentication.inputs import UserCreate
# from database.database import get_db
# from datetime import timedelta
# from logger.logger import get_logger
# from jose import JWTError, jwt
# import os

# router = APIRouter()
# # Function to create access token
# def create_access_token(data: dict, expires_delta: timedelta = timedelta(minutes=30)):
#     to_encode = data.copy()
#     expire = datetime.utcnow() + expires_delta
#     to_encode.update({"exp": expire})
#     encoded_jwt = jwt.encode(to_encode, os.getenv("SECRET_KEY"), algorithm="HS256")
#     return encoded_jwt

# # Function to decode the token
# def decode_token(token: str):
#     try:
#         payload = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=["HS256"])
#         return payload
#     except JWTError:
#         return None

# @router.post("/invite")
# def invite_user_to_department(email: str, department: str, db: Session = Depends(get_db)):
#     logger = get_logger("auth", "auth.log")
#     logger.info(f"Inviting {email} to department {department}")

#     user = db.query(User).filter(User.email == email).first()
    
#     # Check if the user is already in the department before sending the invite
#     if user and user.department and department in user.department:
#         logger.info(f"User {email} is already in department {department}")
#         return {"message": f"User {email} is already in department {department}. No need to send invite."}

#     # Encode department and email in the token
#     payload = {"department": department, "email": email}
#     token = create_access_token(payload, expires_delta=timedelta(minutes=30))

#     # If user does not exist, send signup invitation
#     if not user:
#         signup_link = f"https://your-frontend.com/signup?email={email}&token={token}"

#         email_body = f"""
#         Hi there,

#         You've been invited to join the {department} department on our platform.

#         Please sign up using the link below to complete your registration:
#         {signup_link}

#         Thanks!
#         """
#         send_email(email, "Invitation to sign up", email_body)
#         logger.info(f"Signup invitation sent to {email} for department {department}")
#         return {"message": "Invitation sent for new user to sign up."}

#     # Existing user -> send invitation to join the new department
#     payload = {"sub": email, "department": department, "email": email}  # Include email in the token
#     token = create_access_token(payload, expires_delta=timedelta(minutes=30))
#     accept_link = f"https://your-frontend.com/accept-invite?token={token}"
#     email_body = f"""
#     Hi {user.username},

#     You've been invited to join the {department} department.

#     Click the link below to accept this invitation:
#     {accept_link}

#     This link will expire in 30 minutes.
#     """
#     send_email(user.email, "Invitation to join department", email_body)
#     logger.info(f"Invitation sent to existing user {email} for department {department}")
#     return {"message": "Invitation sent to existing user to join new department."}


# @router.post("/accept-invite")
# def accept_invite(token: str = Query(...), db: Session = Depends(get_db)):
#     logger = get_logger("auth", "auth.log")
#     logger.info(f"Accept invite attempt with token")

#     # Decode the token to get the department and email
#     payload = decode_token(token)
#     if not payload:
#         logger.warning("Invalid or expired invitation token")
#         raise HTTPException(status_code=400, detail="Invalid or expired token")

#     email = payload.get("email")
#     department = payload.get("department")

#     if not email or not department:
#         logger.error("Token missing required data")
#         raise HTTPException(status_code=400, detail="Invalid token payload")

#     user = db.query(User).filter(User.email == email).first()
#     if not user:
#         logger.warning(f"Accept invite failed: user not found for email {email}")
#         raise HTTPException(status_code=404, detail="User not found")

#     # If already in department
#     if user.department and department in user.department:
#         logger.info(f"User {email} already in department {department}")
#         return {"message": f"You are already part of the {department} department."}

#     # Add department
#     if user.department:
#         user.department.append(department)
#     else:
#         user.department = [department]

#     db.commit()
#     logger.info(f"User {email} successfully added to department {department}")

#     return {"message": f"Successfully joined the {department} department."}


# @router.post("/signup")
# def signup(user: UserCreate, token: str, db: Session = Depends(get_db)):
#     logger = get_logger("auth", "auth.log")
#     logger.info(f"Signup attempt for username='{user.username}', email='{user.email}'")

#     # Decode token to get department and email information
#     try:
#         payload = jwt.decode(token, os.getenv("SECRET_KEY"), algorithms=["HS256"])
#         email_from_token = payload["email"]
#         department_from_token = payload["department"]
#     except JWTError:
#         logger.warning(f"Signup failed: Invalid token for email {user.email}")
#         raise HTTPException(status_code=400, detail="Invalid token")

#     # Check if the provided email matches the one in the token
#     if user.email != email_from_token:
#         logger.warning(f"Signup failed: Email mismatch - {user.email} vs {email_from_token}")
#         raise HTTPException(status_code=400, detail="Email mismatch")

#     # Check if username or email already exists
#     existing = db.query(User).filter((User.username == user.username) | (User.email == user.email)).first()
#     if existing:
#         logger.warning(f"Signup failed: Username or email already exists - {user.username} / {user.email}")
#         raise HTTPException(status_code=400, detail="Username or email already exists")

#     # Create a new user and save to the database
#     new_user = User(
#         username=user.username,
#         email=user.email,
#         password_hash=hash_password(user.password),
#         designation=user.designation,
#         department=department_from_token  # Set the department from the token
#     )
#     db.add(new_user)
#     db.commit()
#     db.refresh(new_user)

#     logger.info(f"New user created: user_id={new_user.employee_id}, username={new_user.username}")
#     return {"message": "User created successfully"}
