from sqlalchemy import Column, Integer, String, Double, Float, ForeignKey
from sqlalchemy.orm import relationship
from backend.core.database import Base

# --- SQLAlchemy Models (Database Table Definitions) ---
# FurnitureCoordinates Model: Represents the 'furniture_coordinates' table in your PostgreSQL database
class FurnitureCoordinates(Base):
  __tablename__ = "furniture_coordinates"
  id = Column(Integer, primary_key=True, autoincrement=True)
  generated_room_id = Column(Integer, ForeignKey("generated_rooms.id"),nullable=False)
  # furniture_id = Column(Integer, ForeignKey("furniture.id"), nullable=False)
  x_coordinate = Column(Float, nullable=False)
  y_coordinate = Column(Float, nullable=False)

  # Foreign Key
  generated_room = relationship("GeneratedRoom", back_populates="furniture_coordinates")

  