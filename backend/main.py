import os
import shutil
from io import BytesIO
from typing import Optional, List
from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Double, func, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, Session as DBSession, relationship
from fastapi import FastAPI, HTTPException, Query, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager # Import for lifespan management
from PIL import Image

# --- Configuration & Setup ---
load_dotenv()

# Database Configuration
DB_USER = os.getenv("DB_USER") 
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST") 
DB_NAME = os.getenv("DB_NAME")

# Check if environment variables are loaded
if not all([DB_USER, DB_PASSWORD, DB_HOST, DB_NAME]):
  raise ValueError("Database environment variables not set. Please check the .env file.")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"

# Set up SQLAlchemy Engine and Base
engine = create_engine(DATABASE_URL)
Base = declarative_base()

# Create a session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- Directory to store uploaded and generated images ---
UPLOAD_DIR = "uploads"
GENERATED_DIR = "generated"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(GENERATED_DIR, exist_ok=True)

# Dependency to get a database session for each request 
def get_db():
  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()

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

  # Relationship to RoomDesign
  room_designs = relationship("RoomDesign", back_populates="furniture", cascade="all, delete-orphan")

class RoomDesign(Base):
  __tablename__ = "room_designs"
  id = Column(Integer, primary_key=True, autoincrement=True)
  furniture_id = Column(Integer, ForeignKey('furniture.id', ondelete='CASCADE'), nullable=False)
  original_image_path = Column(String, nullable=False)
  generated_image_path = Column(String, nullable=False)
  design_style = Column(String, nullable=True)
  generation_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))

  furniture = relationship("Furniture", back_populates="room_designs")

# --- Pydantic Models (For API Request/Response Validation) ---

# Pydantic model for request body when adding new furniture
class FurnitureModel(BaseModel):
  id: Optional[int] = None 
  style: Optional[str] = None
  room: Optional[str] = None
  name : Optional[str] = None
  type: Optional[str] = None  
  price: Optional[float] = None
  imageLink: Optional[str] = None
  purchaseLink: Optional[str] = None

  class Config:
    orm_mode = True
    from_attributes = True

class RoomDesignResponse(BaseModel):
  id: int
  furniture_id: int
  original_image_path: str
  generated_image_path: str
  design_style: Optional[str] = None
  generation_date: Optional[datetime] = None

  class Config: 
    orm_mode = True
    from_attributes = True

# --- Lifespan Context Manager for Database Setup ---
@asynccontextmanager
async def lifespan(app: FastAPI):
  """
  Context manager for application startup and shutdown events. 
  Used for creating database tables.
  """
  print("Application startup: Creating database tables...")
  Base.metadata.create_all(engine)
  yield
  print("Application shutdown: No specific cleanup")

# Initialize FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)

# --- CORS Middleware ---
app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],    # Add your frontend URLs
  allow_credentials=True, 
  allow_methods=["*"],    # Allows all methods
  allow_headers=["*"],    # Allows all headers
)

# --- API Endpoints ---

@app.get("/")
def read_root():
  """
  Root endpoint for the Furniture API.
  """
  return {"message": "Welcome to the Furniture API"}

# --- Simulate the upload and generate image endpoints --- 

@app.post("/upload-image/{furniture_id}", response_model=RoomDesignResponse)
async def upload_image(furniture_id: int, file: UploadFile = File(...)):
    """
    Uploads an original image for a furniture item.
    Stores the path in the room_designs table.
    """
    db = SessionLocal()
    try:
        furniture = db.query(Furniture).filter_by(id=furniture_id).first()
        if not furniture:
            raise HTTPException(status_code=404, detail="Furniture not found.")

        extension = os.path.splitext(file.filename)[1].lower()
        if extension not in [".jpg", ".jpeg", ".png"]:
            raise HTTPException(status_code=400, detail="Invalid file type.")

        unique_filename = f"{furniture_id}_{os.urandom(8).hex()}{extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Insert record into room_designs (simulate generated as same image)
        new_design = RoomDesign(
            furniture_id=furniture_id,
            original_image_path=file_path,
            generated_image_path=file_path,  # Initially same
            design_style="original"
        )
        db.add(new_design)
        db.commit()
        db.refresh(new_design)
        return new_design

    finally:
        db.close()

@app.post("/generate-image/{room_design_id}", response_model=RoomDesignResponse)
async def generate_image(room_design_id: int):
    """
    Simulate AI generation by copying the original image as the generated one.
    Updates the generated_image_path in the room_designs table.
    """
    db = SessionLocal()
    try:
        design = db.query(RoomDesign).filter_by(id=room_design_id).first()
        if not design:
            raise HTTPException(status_code=404, detail="RoomDesign not found.")

        original_path = design.original_image_path
        if not os.path.exists(original_path):
            raise HTTPException(status_code=400, detail="Original image missing.")

        # Simulate 'AI generated' image by copying
        filename = os.path.basename(original_path)
        generated_filename = f"generated_{filename}"
        generated_path = os.path.join(GENERATED_DIR, generated_filename)
        shutil.copy(original_path, generated_path)

        design.generated_image_path = generated_path
        design.design_style = "simulated"
        design.generation_date = datetime.now(timezone.utc)

        db.commit()
        db.refresh(design)
        return design
    finally:
        db.close()

@app.get("/view-image/{folder}/{filename}")
def view_image(folder: str, filename: str):
    """
    View uploaded or generated image.
    Example: /view-image/uploads/filename.jpg
    """
    if folder not in ["uploads", "generated"]:
        raise HTTPException(status_code=400, detail="Invalid folder.")
    file_path = os.path.join(folder, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found.")
    return FileResponse(file_path)

# --- POST & GET Furniture Endpoints ---

@app.post("/furniture/", response_model=List[FurnitureModel])
def add_furniture(furniture: FurnitureModel):
  """
  Adds a new furniture item to the database.
  """
  db = SessionLocal()
  try: 
    new_furniture = Furniture(
      style=furniture.style,
      room=furniture.room,
      name=furniture.name,
      type=furniture.type,
      price=furniture.price,
      imageLink=furniture.imageLink,
      purchaseLink=furniture.purchaseLink
    )
    db.add(new_furniture)
    db.commit()
    db.refresh(new_furniture)

    return new_furniture
  except Exception as e:
    db.rollback() # Rollback in case of error
    raise HTTPException(status_code=500, detail=f"Error adding furniture: {str(e)}")
  finally: 
    db.close()

@app.get("/get-furniture", response_model=List[FurnitureModel])
def list_furniture():
  """
  Retrieves all furniture items from the database.
  """
  db = SessionLocal()
  try: 
    # furnitures = session.query(Furniture).order_by(Furniture.id.desc()).all()
    furnitures = db.query(Furniture).all()
    return furnitures
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Error getting furniture list: {str(e)}")
  finally:
    db.close()

@app.get("/get-furniture/filter", response_model=List[FurnitureModel])
def filter_furniture(
  style: str = Query(None, description="Filter by furniture style"),
  room: str = Query(None, description="Filter by room type")
):
  """
  Filters furniture items based on style and room
  Usage:
  /furniture/filter/?style=scandinavian
  /furniture/filter/?room=bed room
  """
  db = SessionLocal()
  try:
    query = db.query(Furniture)

    if style:
      query = query.filter(func.lower(Furniture.style) == style.lower())

    if room:
      query = query.filter(func.lower(Furniture.room) == room.lower())

    filtered_furniture = query.all()

    return filtered_furniture
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Error filtering {str(e)}")
  finally:
    db.close()

@app.get("/get-furniture/{furniture_id}", response_model=FurnitureModel)  
def get_furniture_by_id(furniture_id: int):
  """
  Retrives a single furniture item by its ID.
  """
  db = SessionLocal()
  try:
    furniture = db.query(Furniture).filter_by(id=furniture_id).first()
    if not furniture:
      raise HTTPException(status_code=404, detail="Furniture not found")
    return furniture
  except HTTPException as e:
    raise e
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Error getting furniture: {str(e)}")
  finally: 
    db.close()
  
#---------------------------------------------------------------------------------

# @app.delete("/del-furniture/{furniture_id}")
# def del_furniture(furniture_id: int):
#   """
#   Delete furniture item 
#   """
#   try: 
#     furniture = session.query(Furniture).filter_by(id=furniture_id).first()
#     if furniture:
#       session.delete(furniture)
#       session.commit()
#       print("Furniture successfully deleted.")
#       return {"result": "ok"}
    
#     else:
#       raise HTTPException(status_code=404, detail=f"Furniture not found.")

#   except Exception as e:
#     session.rollback()
#     raise HTTPException(status_code=500, detail=f"Error deleting book: {str(e)}")
    


# @app.put("/update-furniture/{furniture_id}")
# def upd_furniture():
#   """
#   Update furniture item
#   """
#   pass




    