from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# --- Pydantic Schemas for Furniture ---

# Pydantic Schema: Represents the structure of a furniture item

# --- Furniture Database (Renamed) --- 
class FurnitureDatabaseCreate(BaseModel):
  furniture_id: Optional[str] = None
  style: Optional[str] = None
  room: Optional[str] = None
  name: Optional[str] = None
  type: Optional[str] = None
  price: Optional[float] = None
  image_link: Optional[str] = None
  purchase_link: Optional[str] = None

  class Config:
    from_attributes = True # Allows Pydantic to work with SQLAlchemy models directly

class FurnitureDatabaseModel(FurnitureDatabaseCreate):
  id: int

# --- Pydantic Schemas for Generated Rooms ---

# Pydantic Schema: Represents the structure of a generated room
class GeneratedRoomModel(BaseModel):
  id: int
  original_image_path: str
  generated_image_path: str
  generated_room_id: str
  room_style: Optional[str] = None
  design_style: Optional[str] = None
  generated_date: Optional[datetime] = None

  class Config:
    from_attributes = True # Allows Pydantic to work with SQLAlchemy models directly


# --- Pydantic Schemas for Furniture Coordinates ---

# Pydantic Schema: Represents the structure of furniture coordinates
class FurnitureCoordinatesModel(BaseModel):
  id: Optional[int] = None
  generated_room_id: str
  furniture_id: str
  x_coordinate: float
  y_coordinate: float
  type: Optional[str] = None

  class Config:
    from_attributes = True # Allows Pydantic to work with SQLAlchemy models directly

class FurnitureCoordinateCreate(BaseModel):
  furniture_id: str
  x_coordinate: float
  y_coordinate: float
  type: Optional[str] = None

class FurnitureCoordinateBatchCreate(BaseModel):
  generated_room_id: str
  coordinates: List[FurnitureCoordinateCreate]