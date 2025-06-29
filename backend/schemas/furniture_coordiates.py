# from pydantic import BaseModel
# from typing import Optional, List

# # --- Pydantic Schemas for Furniture Coordinates ---

# # Pydantic Schema: Represents the structure of furniture coordinates
# class FurnitureCoordinatesModel(BaseModel):
#   id: Optional[int] = None
#   generated_room_id: Optional[int] = None
#   furniture_id: Optional[int] = None
#   x_coordinate: Optional[float] = None
#   y_coordinate: Optional[float] = None

#   class Config:
#     orm_mode = True  # Allows Pydantic to work with SQLAlchemy models directly
