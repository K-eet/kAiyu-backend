# backend/routers/coordinates.py

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import func
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.models.models import FurnitureCoordinates, FurnitureDatabase, GeneratedRoom
from typing import List
from ultralytics import YOLO
import cv2
import numpy as np
from PIL import Image
import io
from backend.services.similarity import similarity_service

# The prefix is /generated, so all paths here will start with that
router = APIRouter(prefix="/generated", tags=["Furniture Detection & Similarity"])

# Load the YOLO model once
model = YOLO("./backend/best_yolo12n_v6.pt") # Make sure this path is correct

@router.post("/detect-and-find-similar/")
async def detect_save_and_find_similar(
  generated_room_id: str, # Pass the room ID as a query parameter
  db: Session = Depends(get_db),
  file: UploadFile = File(...)
):
  """
  Detects furniture, saves its coordinates to the database, and finds similar products.
  This single endpoint handles the entire post-generation process.
  """
  # --- 1. Validate Input and Load Image ---
  if not file.content_type.startswith('image/'):
    raise HTTPException(status_code=400, detail="File provided is not an image.")

  # Find the corresponding generated room in the database
  room = db.query(GeneratedRoom).filter_by(generated_room_id=generated_room_id).first()
  if not room:
    raise HTTPException(status_code=404, detail="Generated room not found in the database.")

  contents = await file.read()
  nparr = np.frombuffer(contents, np.uint8)
  img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

  if img_bgr is None:
    raise HTTPException(status_code=400, detail="Could not decode image.")

  # --- 2. Run YOLOv8 Inference ---
  h_img, w_img, _ = img_bgr.shape
  results = model(img_bgr, conf=0.5, iou=0.7, verbose=False)

  detected_items_response = []
  
  # Process all detections
  for r in results:
    boxes = r.boxes.xyxy.cpu().numpy()
    confs = r.boxes.conf.cpu().numpy()
    clss = r.boxes.cls.cpu().numpy()
    names = model.names

    for i in range(len(boxes)):
      x1, y1, x2, y2 = map(int, boxes[i])
      class_id = int(clss[i])
      class_name = names[class_id]

      # --- 3. Save Coordinates to Database (Your Original Logic) ---
      # Calculate normalized center coordinates
      center_x = (x1 + x2) / 2 / w_img
      center_y = (y1 + y2) / 2 / h_img

      # Find a matching furniture item in the database to link the coordinate
      furniture_match = db.query(FurnitureDatabase).filter(
        func.lower(FurnitureDatabase.room) == room.room_style.lower(),
        func.lower(FurnitureDatabase.style) == room.design_style.lower(),
        func.lower(FurnitureDatabase.type) == class_name.lower()
      ).first()

      if furniture_match:
        # Create the coordinate object to be saved
        coord = FurnitureCoordinates(
          generated_room_id=generated_room_id,
          furniture_id=furniture_match.furniture_id,
          x_coordinate=center_x,
          y_coordinate=center_y,
          type=class_name
        )
        db.add(coord) # Add to the session

      # --- 4. Find Similar Products (Visual Search) ---
      cropped_item_bgr = img_bgr[y1:y2, x1:x2]
      if cropped_item_bgr.shape[0] > 0 and cropped_item_bgr.shape[1] > 0:
        cropped_item_rgb = cv2.cvtColor(cropped_item_bgr, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(cropped_item_rgb)
        
        similar_products = similarity_service.find_similar_items(
          cropped_image=pil_image,
          class_name=class_name
        )
        
        detected_items_response.append({
          "class_name": class_name,
          "bounding_box": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
          "confidence": float(confs[i]),
          "similar_products": similar_products
        })

  # --- 5. Commit to DB and Return Response ---
  if not detected_items_response:
    db.rollback() # Rollback if no items were detected to avoid empty commits
    return {"message": "No relevant items detected in the image."}
  
  # Commit all new coordinates to the database at once
  db.commit()

  return {"detected_items": detected_items_response}

# # backend/routers/coordinates.py

# from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
# from sqlalchemy import func
# from sqlalchemy.orm import Session
# from backend.core.database import get_db
# from backend.models.models import FurnitureCoordinates, FurnitureDatabase, GeneratedRoom
# from typing import List
# from ultralytics import YOLO
# import cv2
# import numpy as np
# from PIL import Image
# import io
# from backend.services.similarity import similarity_service

# # The prefix is /generated, so all paths here will start with that
# router = APIRouter(prefix="/generated", tags=["Furniture Detection & Similarity"])

# # Load the YOLO model once
# model = YOLO("./backend/best_yolo12n_v6.pt") # Make sure this path is correct

# @router.post("/detect-and-find-similar/")
# async def detect_save_and_find_similar(
#     generated_room_id: str, # Pass the room ID as a query parameter
#     db: Session = Depends(get_db),
#     file: UploadFile = File(...)
# ):
#     """
#     Detects furniture, saves its coordinates to the database, and finds similar products.
#     This single endpoint handles the entire post-generation process.
#     """
#     # --- 1. Validate Input and Load Image ---
#     if not file.content_type.startswith('image/'):
#         raise HTTPException(status_code=400, detail="File provided is not an image.")

#     # Find the corresponding generated room in the database
#     room = db.query(GeneratedRoom).filter_by(generated_room_id=generated_room_id).first()
#     if not room:
#         raise HTTPException(status_code=404, detail="Generated room not found in the database.")

#     contents = await file.read()
#     nparr = np.frombuffer(contents, np.uint8)
#     img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

#     if img_bgr is None:
#         raise HTTPException(status_code=400, detail="Could not decode image.")

#     # --- 2. Run YOLOv8 Inference ---
#     h_img, w_img, _ = img_bgr.shape
#     results = model(img_bgr, conf=0.5, iou=0.7, verbose=False)

#     detected_items_response = []
    
#     # Process all detections
#     for r in results:
#         boxes = r.boxes.xyxy.cpu().numpy()
#         confs = r.boxes.conf.cpu().numpy()
#         clss = r.boxes.cls.cpu().numpy()
#         names = model.names

#         for i in range(len(boxes)):
#             x1, y1, x2, y2 = map(int, boxes[i])
#             class_id = int(clss[i])
#             class_name = names[class_id]

#             # --- 3. Save Coordinates to Database (Your Original Logic) ---
#             # Calculate normalized center coordinates
#             center_x = (x1 + x2) / 2 / w_img
#             center_y = (y1 + y2) / 2 / h_img

#             # Find a matching furniture item in the database to link the coordinate
#             furniture_match = db.query(FurnitureDatabase).filter(
#                 func.lower(FurnitureDatabase.room) == room.room_style.lower(),
#                 func.lower(FurnitureDatabase.style) == room.design_style.lower(),
#                 func.lower(FurnitureDatabase.type) == class_name.lower()
#             ).first()

#             if furniture_match:
#                 # Create the coordinate object to be saved
#                 coord = FurnitureCoordinates(
#                     generated_room_id=generated_room_id,
#                     furniture_id=furniture_match.furniture_id,
#                     x_coordinate=center_x,
#                     y_coordinate=center_y,
#                     type=class_name
#                 )
#                 db.add(coord) # Add to the session

#             # --- 4. Find Similar Products (Visual Search) ---
#             cropped_item_bgr = img_bgr[y1:y2, x1:x2]
#             if cropped_item_bgr.shape[0] > 0 and cropped_item_bgr.shape[1] > 0:
#                 cropped_item_rgb = cv2.cvtColor(cropped_item_bgr, cv2.COLOR_BGR2RGB)
#                 pil_image = Image.fromarray(cropped_item_rgb)
                
#                 similar_products = similarity_service.find_similar_items(
#                     cropped_image=pil_image,
#                     class_name=class_name
#                 )
                
#                 detected_items_response.append({
#                     "class_name": class_name,
#                     "bounding_box": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
#                     "confidence": float(confs[i]),
#                     "similar_products": similar_products
#                 })

#     # --- 5. Commit to DB and Return Response ---
#     if not detected_items_response:
#         db.rollback() # Rollback if no items were detected to avoid empty commits
#         return {"message": "No relevant items detected in the image."}
    
#     # Commit all new coordinates to the database at once
#     db.commit()

#     return {"detected_items": detected_items_response}

