from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from backend.core.database import Base

# --- SQLAlchemy Models (Database Table Definitions) ---
# GeneratedRoom Model: Represents the 'generated_rooms' table in your PostgreSQL database
class GeneratedRoom(Base):
  __tablename__ = "generated_rooms"
  id = Column(Integer, primary_key=True, autoincrement=True)
  original_image_path = Column(String, nullable=False)
  generated_image_path = Column(String, nullable=False)
  room_style = Column(String, nullable=False)
  design_style = Column(String, nullable=False)
  generated_date = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

  # Foreign Key
  furniture_coordinates = relationship("FurnitureCoordinates", back_populates="generated_rooms")
