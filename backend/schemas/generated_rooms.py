from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# --- Pydantic Schemas for Generated Rooms ---

# Pydantic Schema: Represents the structure of a generated room
class GeneratedRoomModel(BaseModel):
  id: int
  original_image_path: str
  generated_image_path: str
  design_style: Optional[str] = None 
  generated_date: Optional[datetime] = None

  class Config: 
    orm_mode = True  # Allows Pydantic to work with SQLAlchemy models directly