# routers/coordinates.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.models.models import FurnitureCoordinates, FurnitureDatabase, GeneratedRoom
from backend.schemas.schemas import (
  FurnitureCoordinatesModel, 
  FurnitureCoordinateBatchCreate)
from typing import List
from ultralytics import YOLO
import cv2
from fastapi.responses import JSONResponse
import os
from fastapi import APIRouter, UploadFile, File, HTTPException
from ultralytics import YOLO
import cv2
import numpy as np
from PIL import Image
import io
from backend.services.similarity import similarity_service # Import the service

router = APIRouter(prefix="/generated", tags=["FurnitureDatabase Coordinates"])
model = YOLO("./backend/best_yolo12n_v6.pt")

def detect_furniture_coordinates(image_path: str):
  """
  Detect furniture objects from the image using YOLOv11 model

  Steps: 
  1. Read the input image.
  2. Run the object detection with YOLOv11.
  3. For each detected object, caclulate its center coordinates (normalized 0-1).
  4. Collect x, y coordinates and label (type) into a list.
  5. Return the list of detected objects.

  Returns: 
    List of dicts: {"x": float, "y": float, "type": str}
  """
  img = cv2.imread(image_path)
  h, w, _ = img.shape
  results = model(image_path, conf=0.2)

  coords_with_labels = []
  if results:
    result = results[0]
    names = result.names
    boxes = result.boxes.xyxy
    classes = result.boxes.cls

    for box, cls_idx in zip(boxes, classes):
      x1, y1, x2, y2 = box.tolist()
      center_x = (x1 + x2) / 2 / w
      center_y = (y1 + y2) / 2 / h
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
  """
  Detect furniture coordinates in a generated room image and store them in the database.

  Steps:
  1. Validate that the given generated_room_id exists.
  2. Load the stored generated room image from disk.
  3. Detect furniture objects using YOLO model (calls detect_furniture_coordinates).
  4. For each detected item:
     - Match it to furniture in the database based on room type, style, and furniture type.
     - Store the normalized x, y coordinates and link them to the generated room and furniture.
  5. Commit all coordinates to the database.
  6. Return the list of saved coordinates.
  
  Raises:
      404 if room not found, image missing, or no furniture detected.
  """
  room = db.query(GeneratedRoom).filter_by(generated_room_id=generated_room_id).first()
  if not room:
    raise HTTPException(status_code=404, detail="Generated room not found")
  
  image_path = room.generated_image_path
  if not os.path.exists(image_path):
    raise HTTPException(status_code=404, detail=f"Image path '{image_path}' not found")

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

@router.post("/detect-and-find-similar/")
async def detect_and_find_similar(file: UploadFile = File(...)):
    """
    Detects furniture in an uploaded image, and for each detected item,
    finds similar products from the catalog.
    """
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File provided is not an image.")

    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img_bgr is None:
        raise HTTPException(status_code=400, detail="Could not decode image.")

    # Run YOLOv8 inference
    results = model(img_bgr, conf=0.5, iou=0.7, verbose=False)

    detected_items = []
    
    # Process results list
    for r in results:
        boxes = r.boxes.xyxy.cpu().numpy()
        confs = r.boxes.conf.cpu().numpy()
        clss = r.boxes.cls.cpu().numpy()
        names = model.names

        for i in range(len(boxes)):
            x1, y1, x2, y2 = map(int, boxes[i])
            class_id = int(clss[i])
            class_name = names[class_id]

            # Crop the detected item from the image
            cropped_item_bgr = img_bgr[y1:y2, x1:x2]
            
            if cropped_item_bgr.shape[0] > 0 and cropped_item_bgr.shape[1] > 0:
                # Convert cropped image to PIL format for the similarity service
                cropped_item_rgb = cv2.cvtColor(cropped_item_bgr, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(cropped_item_rgb)
                
                # Find similar items using the service
                similar_products = similarity_service.find_similar_items(
                    cropped_image=pil_image,
                    class_name=class_name
                )
                
                detected_items.append({
                    "class_name": class_name,
                    "bounding_box": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                    "confidence": float(confs[i]),
                    "similar_products": similar_products
                })

    if not detected_items:
        return {"message": "No relevant items detected in the image."}

    return {"detected_items": detected_items}