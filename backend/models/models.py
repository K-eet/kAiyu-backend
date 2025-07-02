from sqlalchemy import Column, Integer, String, Double, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from backend.core.database import Base
from datetime import datetime, timezone

# --- SQLAlchemy Models (Database Table Definitions) ---

# Furniture Model: Represents the 'furniture' table in your PostgreSQL database
class Furniture(Base):
  __tablename__ = "furniture"
  id = Column(Integer, primary_key=True, autoincrement=True)
  furniture_id = Column(String, nullable=True, unique=True)
  style = Column(String, nullable=True)
  room = Column(String, nullable=True)
  name = Column(String, nullable=True)
  type = Column(String, nullable=True)
  price = Column(Double, nullable=True)
  image_link = Column(String, nullable=True)
  purchase_link = Column(String, nullable=True)

  # Relationships with FurnitureCoordinates
  # This establishes a one-to-many relationship where one piece of furniture can be associated with multiple 
  furniture_coordinates = relationship("FurnitureCoordinates", back_populates="furniture",
                                 cascade="all, delete-orphan")


# GeneratedRoom Model: Represents the 'generated_rooms' table in your PostgreSQL database
class GeneratedRoom(Base):
  __tablename__ = "generated_rooms"
  id = Column(Integer, primary_key=True, autoincrement=True)
  original_image_path = Column(String, nullable=False)
  generated_image_path = Column(String, nullable=False)
  generated_room_id = Column(Integer, nullable=False, unique=True)
  room_style = Column(String, nullable=False)
  design_style = Column(String, nullable=False)
  generated_date = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

  # Foreign Key
  furniture_coordinates = relationship("FurnitureCoordinates",
                                       back_populates="generated_room",
                                       cascade="all, delete-orphan")

# FurnitureCoordinates Model: Represents the 'furniture_coordinates' table in your PostgreSQL database
class FurnitureCoordinates(Base):
  __tablename__ = "furniture_coordinates"
  id = Column(Integer, primary_key=True, autoincrement=True)
  furniture_id = Column(String, ForeignKey("furniture.furniture_id"), nullable=False)
  # generated_room_id = Column(Integer, ForeignKey("generated_rooms.id"),nullable=False)
  generated_room_id = Column(Integer, ForeignKey("generated_rooms.generated_room_id"),nullable=False)
  x_coordinate = Column(Float, nullable=False)
  y_coordinate = Column(Float, nullable=False)

  # Foreign Key
  furniture = relationship("Furniture", back_populates="furniture_coordinates")
  generated_room = relationship("GeneratedRoom", back_populates="furniture_coordinates")
