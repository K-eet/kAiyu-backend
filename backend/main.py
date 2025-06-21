import os
import shutil
from typing import Optional, List
from contextlib import contextmanager

from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Double, func, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, Session as DBSession
from fastapi import FastAPI, HTTPException, Query, File, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from datetime import datetime, timezone
import uuid

app = FastAPI()

# --- CORS Middleware ---
app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],    # Add your frontend URLs
  allow_credentials=True, 
  allow_methods=["*"],    # Allows all methods
  allow_headers=["*"],    # Allows all headers
)

# --- Configuration & Setup ---
load_dotenv()

# Database URL (adjust username/password as needed)
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"

# 'static' directory exists for storing images 
# UPLOAD_DIR = "static/uploads"
# GENERATED_DIR = "static/generated_designs"
# os.makedirs(UPLOAD_DIR, exist_ok=True)
# os.makedirs(GENERATED_DIR, exist_ok=True)

# Set up SQLAlchemy Engine and Base
engine = create_engine(DATABASE_URL)
Base = declarative_base()

# Create a session factory
Session = sessionmaker(bind=engine)
session = Session()
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to get a database session for each request 
# def get_db():
#   db = SessionLocal()
#   try:
#     yield db
#   finally:
#     db.close()

# --- SQLAlchemy Models (Database Table Definitions) ---

# Furniture Model: Represents the 'furniture' table in your PostgreSQL database
class Furniture(Base):
  __tablename__ = "furniture"
  id = Column(Integer, primary_key=True, autoincrement=True)
  style = Column(String, nullable=True)
  room = Column(String, nullable=True)
  name = Column(String, nullable=True)
  type = Column(String, nullable=True)
  price = Column(Double, nullable=True)
  imageLink = Column(String, nullable=True)
  purchaseLink = Column(String, nullable=True)

# RoomDesign Model: Represents the 'room_designs' table for AI generated images
# class RoomDesign(Base):
#   __tablename__ = "room_designs"
#   id = Column(Integer, primary_key=True, autoincrement=True)
#   original_image_path = Column(String, nullable=False)
#   generated_image_path = Column(String, nullable=True)
#   design_style = Column(String, nullable=True)
#   created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# Create tables in the database
Base.metadata.create_all(engine)

# --- Pydantic Models (For API Request/Response Validation)

# Pydantic model for request body when adding new furniture
class FurnitureModel(BaseModel):
  style: Optional[str] = None
  room: Optional[str] = None
  name : Optional[str] = None
  type: Optional[str] = None  
  price: Optional[float] = None
  imageLink: Optional[str] = None
  purchaseLink: Optional[str] = None


# --- API Endpoints ---

@app.get("/")
def read_root():
  """
  Root endpoint for the Furniture API.
  """
  return {"message": "Welcome to the Furniture API"}

@app.post("/furniture/")
def add_furniture(furniture: FurnitureModel):
  """
  Adds a new furniture item to the database.
  """
  try: 
    new_furniture = Furniture(
      id=furniture.id,
      style=furniture.style,
      room=furniture.room,
      name=furniture.name,
      type=furniture.type,
      price=furniture.price,
      imageLink=furniture.imageLink,
      purchaseLink=furniture.purchaseLink
    )
    session.add(new_furniture)
    session.commit()
    session.refresh(new_furniture)

    return {
      "id": new_furniture.id,
      "data": new_furniture
    }
  except Exception as e:
    session.rollback() # Rollback in case of error
    raise HTTPException(status_code=500, detail=f"Error adding furniture: {str(e)}")

@app.get("/get-furniture")
def list_furniture():
  """
  Retrieves all furniture items from the database.
  """
  try: 
    # furnitures = session.query(Furniture).order_by(Furniture.id.desc()).all()
    furnitures = session.query(Furniture).all()
    return furnitures
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Error getting furniture list: {str(e)}")

@app.get("/get-furniture/filter")
def filter_furniture(
  style: str = Query(None, description="Filter by furniture style"),
  room: str = Query(None, description="Filter by room type")
):
  """
  Filters furniture items based on style and room
  Usage:
  /furniture/filter/?style=scandinavian
  /furniture/filter/?room=bedroom
  """

  try:
    query = session.query(Furniture)

    if style:
      query = query.filter(func.lower(Furniture.style) == style.lower())

    if room:
      query = query.filter(func.lower(Furniture.room) == room.lower())

    filtered_furniture = query.all()

    if not filtered_furniture:
      return {"message": "No furniture found matching the criteria."}
      
    return filtered_furniture  
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Error filtering {str(e)}")

@app.get("/get-furniture/{furniture_id}")  
def list_furniture(furniture_id: int):
  """
  Retrives a single furniture item by its ID.
  """
  try:
    furniture = session.query(Furniture).filter_by(id=furniture_id).first()
    if not furniture:
      raise HTTPException(status_code=404, detail="Furniture not found")
    return furniture
  except HTTPException as e:
    raise e
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Error getting furniture: {str(e)}")
  
#---------------------------------------------------------------------------------

# Define the directory where uploaded files will be stored
UPLOAD_DIRECTORY = "uploaded_files"

# Create the upload directory if it doesn't exist
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)

@app.post("/upload-image/")
async def upload_image(file: UploadFile = File(...)):
  """
  Uploads an image file to the server.
  The file will be saved in the 'uploaded_files' directory.
  """
  try:
    # Ensure the file is an image (optional, but good practice)
    if not file.content_type.startswith("image/"):
      raise HTTPException(status_code=400, detail="Only image files are allowed.")

    # Create a unique filename to avoid overwriting existing files
    # You might want to use UUID for more robust unique filenames in a real app
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{os.urandom(8).hex()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIRECTORY, unique_filename)

    # Save the uploaded file synchronously (for small to medium files)
    # For very large files, consider using async file operations (aiofiles)
    with open(file_path, "wb") as buffer:
      shutil.copyfileobj(file.file, buffer)
    
    return {"message": f"File '{file.filename}' uploaded successfully as '{unique_filename}'", "filename": unique_filename}
  except HTTPException as e:
    raise e # Re-raise FastAPI HTTPExceptions
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

@app.get("/download-image/{filename}")
async def download_image(filename: str):
  """
  Downloads an image file from the server.
  The file must exist in the 'uploaded_files' directory.
  """
  file_path = os.path.join(UPLOAD_DIRECTORY, filename)

  # Check if the file exists
  if not os.path.exists(file_path):
    raise HTTPException(status_code=404, detail="File not found")
  
  # Return the file as a FileResponse
  # FastAPI will automatically set the Content-Type header based on the file extension
  # and handle streaming the file.
  return FileResponse(path=file_path, filename=filename, media_type="image/*")

# --- Optional: Endpoint to list uploaded files (useful for testing) ---
@app.get("/list-uploaded-files/")
def list_uploaded_files():
  """
  Lists all files currently in the 'uploaded_files' directory.
  """
  try:
    files = os.listdir(UPLOAD_DIRECTORY)
    return {"uploaded_files": files}
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Error listing files: {str(e)}")

@app.delete("/del-furniture/{furniture_id}")
def del_furniture(furniture_id: int):
  """
  Delete furniture item 
  """
  try: 
    furniture = session.query(Furniture).filter_by(id=furniture_id).first()
    if furniture:
      session.delete(furniture)
      session.commit()
      print("Furniture successfully deleted.")
      return {"result": "ok"}
    
    else:
      raise HTTPException(status_code=404, detail=f"Furniture not found.")

  except Exception as e:
    session.rollback()
    raise HTTPException(status_code=500, detail=f"Error deleting book: {str(e)}")
    


# @app.put("/update-furniture/{furniture_id}")
# def upd_furniture():
#   """
#   Update furniture item
#   """
#   pass




    