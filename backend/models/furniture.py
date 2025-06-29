from sqlalchemy import Column, Integer, String, Double, Float
from sqlalchemy.orm import relationship
from backend.core.database import Base

# --- SQLAlchemy Models (Database Table Definitions) ---

# Furniture Model: Represents the 'furniture' table in your PostgreSQL database

class Furniture(Base):
  __tablename__ = "furniture"
  id = Column(Integer, primary_key=True, autoincrement=True)
  style = Column(String, nullable=True)
  room = Column(String, nullable=True)
  name = Column(String, nullable=True)
  type = Column(String, nullable=True)
  price = Column(Double, nullable=True)
  image_link = Column(String, nullable=True)
  purchase_link = Column(String, nullable=True)

  # Relationships with FurnitureCoordinates
  # This establishes a one-to-many relationship where one piece of furniture can be associated with multiple 
  # generated_rooms = relationship("FurnitureCoordinates", back_populates="furniture",
  #                                cascade="all, delete-orphan")

