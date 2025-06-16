from sqlalchemy import create_engine, Column, Integer, String, Double, func
from sqlalchemy.orm import sessionmaker, declarative_base
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI()
app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],    # Add your frontend URLs
  allow_credentials=True, 
  allow_methods=["*"],    # Allows all methods
  allow_headers=["*"],    # Allows all headers
)

# Database URL (adjust username/password as needed)
DB_USER = "postgres"
DB_PASSWORD = "password"
DB_HOST = "localhost"
DB_NAME = "furniture_db"
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"

# Set up SQLAlchemy Engine and Base
engine = create_engine(DATABASE_URL)
Base = declarative_base()

# Create a session factory
Session = sessionmaker(bind=engine)
session = Session()

# Define a sample model 
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

# Create the table in the database
Base.metadata.create_all(engine)

# Pydantic model for request body
class FurnitureModel(BaseModel):
  style: Optional[str] = None
  room: Optional[str] = None
  name : Optional[str] = None
  type: Optional[str] = None  
  price: Optional[float] = None
  imageLink: Optional[str] = None
  purchaseLink: Optional[str] = None

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
  
@app.get("/furniture/filter")
def filter_furniture(
  style: Optional[str] = Query(None, description="Filter by furniture style"),
  room: Optional[str] = Query(None, description="Filter by room type")
):
  """
  Filters furniture items based on style and room
  Usage:
  /furniture/filter/?style=Scandinavian
  /furniture/filter/?room=Bedroom
  """

  try:
    query = session.query(Furniture)

    if style:
      query = query.filter(Furniture.style.ilike(f"%{style}%"))

    if room:
      query = query.filter(Furniture.room.ilike(f"%{room}%"))
    
    filtered_furniture = query.all()

    if not filtered_furniture:
      return {"message": "No furniture found matching the criteria."}
      
    return filtered_furniture  
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Error filtering str{e}")



# Filter by Room type (E.g. Scandinavian, bedroom)
# @app.get("/get-furniture/style/{style}")
# def get_furniture_by_style(style: str):
#   try:
#     furnitures = session.query(Furniture).filter(
#       Furniture.style.ilike(f"%{style}%")
#     ).all()

#     if not furnitures:
#       return {"message": f"No furniture found with style: {style}", "data":[]}
#   except Exception as e:
#     raise HTTPException(status_code=500, detail=f"Error filtering by style: {str(e)}")




    