from fastapi import FastAPI, APIRouter, Depends, HTTPException, Path
from sqlalchemy import func
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.models.models import FurnitureCoordinates, Furniture, GeneratedRoom
from backend.schemas.schemas import (
  FurnitureCoordinatesModel, 
  FurnitureCoordinateCreate, 
  FurnitureCoordinateBatchCreate)
from typing import List
from random import uniform


router = APIRouter(prefix="/generated", tags=["Furniture Coordinates"])

@router.post("/coordinates/batch", response_model=List[FurnitureCoordinatesModel])
def create_coordinates_batch(
	payload: FurnitureCoordinateBatchCreate,
	db: Session = Depends(get_db)
):
	"""
	Insert multiple furniture coordinate hotspots for a generated room.

	Validates:
	- The generated_room_id exists
	- Each furniture_id exists and matches the room + style
	"""
	# Validate Generated Room
	generated_room = db.query(GeneratedRoom).filter_by(generated_room_id=payload.generated_room_id).first()

	if not generated_room:
		raise HTTPException(status_code=400, detail=f"Generated Room ID '{payload.generated_room_id}' not found.")

	created_coords = []

	for coord in payload.coordinates:
		# Validate Furniture ID
		furniture = db.query(Furniture).filter_by(furniture_id=coord.furniture_id).first()
		if not furniture:
			raise HTTPException(status_code=400, detail=f"Furniture ID '{coord.furniture_id}' does not exist.")

			# Validate Room and Style Compatibility
		if furniture.room.lower() != generated_room.room_style.lower() or \
			furniture.style.lower() != generated_room.design_style.lower():
			raise HTTPException(
				status_code=400,
				detail=(
					f"Furniture '{coord.furniture_id}' has room/style ({furniture.room}, {furniture.style}) "
					f"which does not match Generated Room ({generated_room.room_style}, {generated_room.design_style})."
					)
			)

			# Add coordinate to DB session
		new_coord = FurnitureCoordinates(
				generated_room_id=payload.generated_room_id,
				furniture_id=coord.furniture_id,
				x_coordinate=coord.x_coordinate,
				y_coordinate=coord.y_coordinate
		)
		
		db.add(new_coord)
		created_coords.append(new_coord)

	# Commit once after all are added
	db.commit()

	# Refresh all inserted entries to return them properly
	for coord in created_coords:
			db.refresh(coord)

	return created_coords

@router.get("/coordinates/{room_id}", response_model=List[FurnitureCoordinatesModel])
def  get_coordinates(room_id: str, db: Session = Depends(get_db)):
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

@router.post("/coordinates/auto-generate", response_model=List[FurnitureCoordinatesModel])
def auto_generate_coordinates(
		generated_room_id: str,
		db: Session = Depends(get_db)
	):
		"""
		Simulate AI model generating (x, y) furniture coordinates based on room type and style.
		Automatically links matching furniture to the generated room.
		"""
		# Get the room details
		room = db.query(GeneratedRoom).filter_by(generated_room_id=generated_room_id).first()
		if not room:
				raise HTTPException(status_code=404, detail="Generated room not found")

		# Filter furniture for that room/style
		furniture_items = db.query(Furniture).filter(
				func.lower(Furniture.room) == room.room_style.lower(),
				func.lower(Furniture.style) == room.design_style.lower()
		).all()

		if not furniture_items:
			raise HTTPException(status_code=404, detail="No matching furniture")

		# Simulate AI (random x/y or predefined pattern)
		import random
		# coordinates = []
		# for furniture in furniture_items:
		# 	x = round(random.uniform(0.1, 0.9), 2)
		# 	y = round(random.uniform(0.1, 0.9), 2)
		# 	coord = FurnitureCoordinates(
		# 			generated_room_id=generated_room_id,
		# 			furniture_id=furniture.furniture_id,
		# 			x_coordinate=x,
		# 			y_coordinate=y
		# 		)
		# 	db.add(coord)
		# 	coordinates.append(coord)

		# db.commit()
		# return coordinates

		num_to_generate = random.randint(3, min(8, len(furniture_items)))
		selected_furniture = random.sample(furniture_items, num_to_generate)

		coordinates = []
		for furniture in selected_furniture:
			x = round(random.uniform(0.1, 0.9), 2)
			y = round(random.uniform(0.1, 0.9), 2)

			coord = FurnitureCoordinates(
				generated_room_id=generated_room_id,
				furniture_id=furniture.furniture_id,
				x_coordinate=x,
				y_coordinate=y
			)
			db.add(coord)
			coordinates.append(coord)

		db.commit()
		return coordinates
