from fastapi import FastAPI, APIRouter, Depends, HTTPException, Path
from sqlalchemy import func
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.models.models import FurnitureCoordinates, FurnitureDatabase, GeneratedRoom
from backend.schemas.schemas import (
  FurnitureCoordinatesModel, 
  FurnitureCoordinateCreate, 
  FurnitureCoordinateBatchCreate)
from typing import List
from random import uniform
from ultralytics import YOLO
import cv2
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/generated", tags=["FurnitureDatabase Coordinates"])

model = YOLO("./backend/best_v6.pt")

def detect_furniture_coordinates(image_path: str):
	"""
	Function to detect the furniture
	"""
	results = model(image_path, conf=0.3)

	coords_with_labels = []
	if results: 
		result = results[0]
		names = result.names
		boxes = result.boxes.xyxy
		classes = result.boxes.cls

		for box, cls_idx in zip(boxes, classes):
			x1, y1, x2, y2 = box.tolist()
			center_x = int((x1 + x2) / 2)
			center_y = int((y1 + y2) / 2)
			label = names[int(cls_idx)]

			coords_with_labels.append({
				"x": center_x,
				"y": center_y,
				"type": label
			})
	return coords_with_labels

@router.post("/object-detection", response_model=List[FurnitureCoordinatesModel])
def detect_and_store_coordinates(
	generated_room_id: str, 
	db: Session = Depends(get_db)
):
	room = db.query(GeneratedRoom).filter_by(generated_room_id=generated_room_id).first()
	if not room: 
		raise HTTPException(status_code=404, detail="Generated room not found")
	
	image_path = room.generated_image_path
	detected_item = detect_furniture_coordinates(image_path)

	if not detected_item: 
		raise HTTPException(status_code=404, detail="No furniture detected")
	
	coordinates = []

	for item in detected_item: 
		furniture_match = db.query(FurnitureDatabase).filter(
			func.lower(FurnitureDatabase.room) == room.room_style.lower(),
			func.lower(FurnitureDatabase.style) == room.design_style.lower(),
			func.lower(FurnitureDatabase.type) == item["type"].lower()
		).first()

		if not furniture_match: 
			continue

		coord = FurnitureCoordinates(
			generated_room_id=generated_room_id,
			furniture_id = furniture_match.furniture_id,
			x_coordinate = item["x"],
			y_coordinate = item["y"],
			type = item["type"]
		)

		db.add(coord)
		coordinates.append(coord)

	db.commit()
	for coord in coordinates:
		db.refresh(coord)

	return coordinates
	
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
		# Validate FurnitureDatabase ID
		furniture = db.query(FurnitureDatabase).filter_by(furniture_id=coord.furniture_id).first()
		if not furniture:
			raise HTTPException(status_code=400, detail=f"FurnitureDatabase ID '{coord.furniture_id}' does not exist.")

			# Validate Room and Style Compatibility
		if furniture.room.lower() != generated_room.room_style.lower() or \
			furniture.style.lower() != generated_room.design_style.lower():
			raise HTTPException(
				status_code=400,
				detail=(
					f"FurnitureDatabase '{coord.furniture_id}' has room/style ({furniture.room}, {furniture.style}) "
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
    Automatically links matching furniture type to the generated room.
    """
    # Example YOLO output types
    detected_types = ["SOFA", "BED", "CHAIR", "COFFEE TABLE"]  # Simulated detection

    room = db.query(GeneratedRoom).filter_by(generated_room_id=generated_room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Generated room not found")

    coordinates = []

    import random

    for detected_type in detected_types:
        # Find matching furniture item from database based on type
        matching_furniture = db.query(FurnitureDatabase).filter(
            func.lower(FurnitureDatabase.room) == room.room_style.lower(),
            func.lower(FurnitureDatabase.style) == room.design_style.lower(),
            func.lower(FurnitureDatabase.type) == detected_type.lower()
        ).all()

        if not matching_furniture:
            # Skip if no match found
            continue

        selected_furniture = random.choice(matching_furniture)

        x = round(random.uniform(0.1, 0.9), 2)
        y = round(random.uniform(0.1, 0.9), 2)

        coord = FurnitureCoordinates(
            generated_room_id=generated_room_id,
            furniture_id=selected_furniture.furniture_id,
            x_coordinate=x,
            y_coordinate=y,
            type=detected_type  # Assuming your model has added this column
        )
        db.add(coord)
        coordinates.append(coord)

    db.commit()
    return coordinates