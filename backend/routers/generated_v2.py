from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timezone
from backend.core.database import get_db
from backend.models.models import GeneratedRoom, Furniture, FurnitureCoordinates
from backend.schemas.schemas import GeneratedRoomModel, FurnitureCoordinatesModel
import os, shutil, uuid, re
from fastapi.responses import FileResponse
from typing import List

# YOLO Object Detection
from ultralytics import YOLO
import cv2 
import numpy as np

# Stable Diffusion
from diffusers import StableDiffusionImg2ImgPipeline
import torch
from PIL import Image
from io import BytesIO

from backend.core.config import UPLOAD_DIR, GENERATED_DIR

router = APIRouter(prefix="/generated", tags=["Generated Rooms"])

# Load model once
device = "cuda" if torch.cuda.is_available() else "cpu"
pipe = StableDiffusionImg2ImgPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float16 if device == "cuda" else torch.float32,
    use_safetensors=True
).to(device)

# Load YOLO model globally to avoid re
yolo_model = YOLO("backend/yolo11n.pt")

@router.post("/generate-image/", response_model=GeneratedRoomModel)
def upload_and_generate_image(
  file : UploadFile = File(..., description="Upload empty room"),
  room_style: str = Form(..., description="e.g. Bedroom, Living Room"),
  design_style: str = Form(..., description="e.g. Modern, Scandinavian"),
  db: Session = Depends(get_db)
  ):
  """
  Upload image + room & design style -> filters furniture -> simulates image generation 
  """

  # 1. Save uploaded image
  ext = os.path.splitext(file.filename)[1].lower()
  if ext not in [".jpg", ".jpeg", ".png"]:
      raise HTTPException(status_code=400, detail="Invalid file type")
  filename = f"{uuid.uuid4().hex}{ext}"
  file_path = os.path.join(UPLOAD_DIR, filename)
  with open(file_path, "wb") as buffer:
      shutil.copyfileobj(file.file, buffer)

  # 2. Generate custom room ID
  today_str = datetime.now().strftime("%y%m%d")
  id_prefix = f"R-{today_str}"
  latest = db.query(GeneratedRoom.generated_room_id).filter(
      GeneratedRoom.generated_room_id.like(f"{id_prefix}-%")
  ).order_by(desc(GeneratedRoom.id)).first()
  next_id = f"{id_prefix}-{int(latest[0].split('-')[-1])+1:03}" if latest else f"{id_prefix}-001"

  # 3. Create DB record
  room = GeneratedRoom(
      original_image_path=file_path,
      generated_image_path="",
      generated_room_id=next_id,
      room_style=room_style,
      design_style=design_style,
  )
  db.add(room)
  db.commit()
  db.refresh(room)


  # 4. Generate with Stable Diffusion
  try:
      input_img = Image.open(file_path).convert("RGB").resize((512, 512))
      prompt = f"Decorate this {room_style.lower()} with {design_style.lower()} furniture, clean and modern"
      generated = pipe(prompt=prompt, image=input_img, strength=0.75, guidance_scale=7.5).images[0]

      gen_filename = f"generated_{filename}"
      gen_path = os.path.join(GENERATED_DIR, gen_filename)
      generated.save(gen_path)

      room.generated_image_path = gen_path
      room.generated_date = datetime.now(timezone.utc)
      db.commit()
      db.refresh(room)
  except Exception as e:
      raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")

  # 5. Object Detection with YOLO
  try:
      results = yolo_model.predict(source=gen_path, save=False)
      print("YOLO detections:")
      for i, box in enumerate(results[0].boxes.xyxy):
          class_id = int(results[0].boxes.cls[i].item())
          class_name = results[0].names[class_id]
          print(f"Detected: {class_name} at {box.tolist()}")

      # Print YOLO label list
      labels = results[0].names
      print("YOLO labels:", labels)

      # Fetch matching furniture from DB
      furniture_matches = db.query(Furniture).filter(
          func.lower(Furniture.room) == room_style.lower(),
          func.lower(Furniture.style) == design_style.lower()
      ).all()

      print("Furniture from DB:", [f.name.lower() for f in furniture_matches])
      boxes = results[0].boxes.xyxy.cpu().numpy()
      class_ids = results[0].boxes.cls.cpu().numpy().astype(int)
      labels = results[0].names  # class id to name mapping

      furniture_matches = db.query(Furniture).filter(
          func.lower(Furniture.room) == room_style.lower(),
          func.lower(Furniture.style) == design_style.lower()
      ).all()

      # Create a map: type (e.g., "SOFA") ➝ list of Furniture objects
      from collections import defaultdict
      type_to_furnitures = defaultdict(list)
      for f in furniture_matches:
          type_to_furnitures[f.type.strip().lower()].append(f)

      # Iterate over all detected boxes
      for i, box in enumerate(boxes):
          class_name = labels[class_ids[i]].lower()

          # Normalize mapping (e.g., couch → sofa)
          yolo_to_type = {
              "couch": "sofa",
              "tv": "tv",
              "potted plant": "plant",
              "chair": "chair",
              "bed": "bed",
              "lamp": "lamp",
              "dining table": "table",
              "coffee table": "table"
              # Add more mappings if needed
          }

          f_type = yolo_to_type.get(class_name)
          if not f_type or f_type not in type_to_furnitures:
              continue

          # Use first matching furniture (or improve later with logic)
          furniture = type_to_furnitures[f_type][0]
          furniture_id = furniture.furniture_id

          x1, y1, x2, y2 = box
          center_x = round((x1 + x2) / 2 / 512, 2)
          center_y = round((y1 + y2) / 2 / 512, 2)

          coord = FurnitureCoordinates(
              generated_room_id=next_id,
              furniture_id=furniture_id,
              x_coordinate=center_x,
              y_coordinate=center_y
          )
          db.add(coord)

      db.commit()
  except Exception as e:
      raise HTTPException(status_code=500, detail=f"Object detection failed: {str(e)}")

  return room


@router.get("/view/{folder}/{filename}")
def view_image(folder: str, filename: str):
  """
  This GET endpoint function is just to view the generated image. 
  """
  # if folder not in ["uploads", "generated"]:
  #     raise HTTPException(status_code=400, detail="Invalid folder")

  VALID_FOLDERS = {"uploads":  UPLOAD_DIR, "generated": GENERATED_DIR}

  path = os.path.join(VALID_FOLDERS[folder], filename)
  if not os.path.exists(path):
    raise HTTPException(status_code=404, detail="Image not found")

  return FileResponse(path, media_type="image/jpeg")

@router.get("/gallery", response_model=List[GeneratedRoomModel])
def get_all_generated_rooms(db: Session = Depends(get_db)):
  """
  Get all previously generated room records (for gallery view).
  """
  rooms = db.query(GeneratedRoom).order_by(desc(GeneratedRoom.generated_date)).all()
  return rooms
