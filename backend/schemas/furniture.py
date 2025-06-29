from pydantic import BaseModel
from typing import Optional, List

# --- Pydantic Schemas for Furniture ---

# Pydantic Schema: Represents the structure of a furniture item
class FurnitureModel(BaseModel):
  id: Optional[int] = None
  style: Optional[str] = None
  room: Optional[str] = None
  name: Optional[str] = None
  type: Optional[str] = None
  price: Optional[float] = None
  image_link: Optional[str] = None
  purchase_link: Optional[str] = None

  class Config: 
    orm_mode = True  # Allows Pydantic to work with SQLAlchemy models directly