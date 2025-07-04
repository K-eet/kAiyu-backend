from fastapi import FastAPI, APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.models.models import FurnitureCoordinates, Furniture, GeneratedRoom
from backend.schemas.schemas import (
  FurnitureCoordinatesModel, 
  FurnitureCoordinateCreate, 
  FurnitureCoordinateBatchCreate)
from typing import List

router = APIRouter(prefix="/generated", tags=["Furniture Coordinates"])

@router.post("/coordinates/batch", response_model=List[FurnitureCoordinatesModel])
def create_coordinates_batch(
	payload: FurnitureCoordinateBatchCreate,
	db: Session = Depends(get_db)
	):
	"""
	Insert multiple furniture coordinate hotspots for a generated room.
	Validation:
	- Each furniture ID must exist in the database.
	- Furniture's room & style must match the GeneratedRoom's room_style & design_style.
	"""
	created = []

	generated_room = db.query(GeneratedRoom).filter_by(
	generated_room_id=payload.generated_room_id
	).first()

	if not generated_room:
		raise HTTPException(status_code=400, detail=f"Generated Room ID '{payload.generated_room_id}' not found.")

	for coord in payload.coordinates:
		furniture = db.query(Furniture).filter_by(furniture_id=coord.furniture_id).first()

	if not furniture:
		raise HTTPException(
		status_code=400,
		detail=f"Furniture ID '{coord.furniture_id}' does not exist."
		)

	if (furniture.room.lower() != generated_room.room_style.lower() or
	furniture.style.lower() != generated_room.design_style.lower()):
		raise HTTPException(
		status_code=400,
		detail=(
		f"Furniture '{coord.furniture_id}' has room/style ({furniture.room}, {furniture.style}) "
		f"which does not match Generated Room ({generated_room.room_style}, {generated_room.design_style})."
		)
	)

	new_coord = FurnitureCoordinates(
		generated_room_id=payload.generated_room_id,
		furniture_id=coord.furniture_id,
		x_coordinate=coord.x_coordinate,
		y_coordinate=coord.y_coordinate
	)
	db.add(new_coord)
	created.append(new_coord)

	db.commit()
	return created


@router.get("/coordinates/{room_id}", response_model=List[FurnitureCoordinatesModel])
def  get_coordinates(room_id: int, db: Session = Depends(get_db)):
	"""
	Get all furniture coordinates for a specific generated room.

	- Input: generated_room_id as path parameter
	- Output: List of (furniture_id, x_coordinate, y_coordinate) for that room

	Example use case:
	When loading the generated design in the frontend, use this to retrieve 
	the clickable hotspot data and link it to the displayed furniture.
	"""
	coords = db.query(FurnitureCoordinates).filter_by(generated_room_id=room_id).all()
	if not coords: 
		raise HTTPException(status_code=404, detail="No coordinates found for this room")
	return coords

# @router.post("/coordinates/batch", response_model=List[FurnitureCoordinatesModel])
# def create_coordinates_batch(
#   payload: FurnitureCoordinateBatchCreate,
#   db: Session = Depends(get_db)
# ):
#   """
#   Insert multiple furniture coordinate hotspots for a specific generated room.

#   Payload contains:
#   - generated_room_id: The ID of the room the furniture belongs to
#   - coordinates: List of (furniture_id, x, y) tuples

#   Example use case:
#   After AI generates a furnished image, it detects furniture positions and 
#   sends all coordinates to this endpoint in a single batch insert.
#   """
#   created = []

#   for coord in payload.coordinates:
#     new_coord = FurnitureCoordinates(
#       generated_room_id = payload.generated_room_id,
#       furniture_id = coord.furniture_id,
#       x_coordinate = coord.x_coordinate,
#       y_coordinate = coord.y_coordinate
#     )
#     db.add(new_coord)
#     created.append(new_coord)

#   db.commit()
#   return created