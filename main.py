from sqlalchemy import create_engine, Column, Integer, String, Double
from sqlalchemy.orm import sessionmaker, declarative_base
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

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
  return {"message": "Welcome to the Furniture API"}

@app.post("/furniture/")
def add_furniture(furniture: FurnitureModel):
  try: 
    new_furniture = Furniture(
      style=furniture.style,
      name=furniture.name,
      type=furniture.type,
      price=furniture.price,
      imageLink=furniture.imageLink,
      purchaseLink=furniture.purchaseLink
    )
    session.add(new_furniture)
    session.commit()

    return {
      "id": new_furniture.id,
      "data": new_furniture
    }
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Error adding furniture: {str(e)}")
  
@app.get("/get-furniture}")
def list_furniture():
  try: 
    furnitures = session.query(Furniture).order_by(Furniture.id.desc()).all()

    return furnitures
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Error getting book: {str(e)}")

@app.get("/get-furniture/{furniture_id}")  
def list_furniture(furniture_id: int):
  try:
    furniture = session.query(Furniture).filter_by(id=furniture_id).order_by(Furniture.id.desc()).first()
    if not furniture:
      return {"result": "no furniture found"}
    return furniture
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Error getting furniture: {str(e)}")


    