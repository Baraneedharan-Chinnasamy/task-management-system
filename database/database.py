import os
import urllib.parse
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

# Load environment variables
load_dotenv()

DB_USER = urllib.parse.quote_plus(os.getenv("DB_USER"))
DB_PASSWORD = urllib.parse.quote_plus(os.getenv("DB_PASSWORD"))
DB_HOST = os.getenv("DB_HOST")

# Database connection URL (Fixed for employeee_task)
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/employeee_task"

# Create the engine and session maker
engine = create_engine(DATABASE_URL,pool_size=80,max_overflow=20,pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Function to get the database session (for FastAPI)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


