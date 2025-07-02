# from pydantic import BaseModel
# from typing import Optional, List

# # --- Pydantic Schemas for Furniture Coordinates ---

# # Pydantic Schema: Represents the structure of furniture coordinates
# class FurnitureCoordinatesModel(BaseModel):
#   id: Optional[int] = None
#   generated_room_id: int
#   furniture_id: str
#   x_coordinate: float
#   y_coordinate: float

#   class Config:
#     orm_mode = True  # Allows Pydantic to work with SQLAlchemy models directly
