import os
from dotenv import load_dotenv

# Configuration & Setup for the application
load_dotenv()

# Database configuration
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")

# Check if all environment variables are loaded correctly
if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_NAME]):
  raise ValueError("Database environment variables not set. Please check the .env file.")

# Construct the database URL for SQLAlchemy
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

# Directory paths for file uploads and generated images
UPLOAD_DIR = "uploads"
GENERATED_DIR = "generated"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(GENERATED_DIR, exist_ok=True)