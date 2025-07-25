import os
import shutil
import re
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Form
from fastapi.responses import FileResponse
from sqlalchemy import func, desc
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from backend.core.config import UPLOAD_DIR, GENERATED_DIR
from backend.core.database import get_db
from backend.models.models import Furniture, GeneratedRoom, FurnitureCoordinates
from backend.schemas.schemas import FurnitureCreate, FurnitureModel, GeneratedRoomModel, FurnitureCoordinatesModel
import uuid
from typing import List

router = APIRouter(prefix="/generated", tags=["Generated Rooms"])

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
  # 1. Validate and save uploaded image
  ext = os.path.splitext(file.filename)[1].lower()
  if ext not in [".jpg", ".jpeg", ".png"]:
    raise HTTPException(status_code=400, detail="Invalid file type")

  filename = f"{uuid.uuid4().hex}{ext}"
  file_path = os.path.join(UPLOAD_DIR, filename)

  with open(file_path, "wb") as buffer: 
    shutil.copyfileobj(file.file, buffer)

  # 2. Determine next generated_room_id
  # latest = db.query(func.max(GeneratedRoom.generated_room_id)).scalar()
  # next_generated_room_id = 1 if latest is None else latest + 1 
  # try:
  #   latest_id_obj = db.query(GeneratedRoom.generated_room_id).filter(
  #       GeneratedRoom.generated_room_id.like("R%")
  #   ).order_by(desc(GeneratedRoom.id)).first()

  #   if latest_id_obj and latest_id_obj[0].startswith("R"):
  #       latest_number = int(re.sub("[^0-9]", "", latest_id_obj[0]))
  #       next_generated_room_id = f"R{latest_number + 1}"
  #   else:
  #       next_generated_room_id = "R1"
  # except Exception as e:
  #   raise HTTPException(status_code=500, detail=f"Error generating ID: {str(e)}")
  try: 
    today_str = datetime.now().strftime("%y%m%d")
    id_prefix = f"R-{today_str}"

    latest_id_obj = db.query(GeneratedRoom.generated_room_id).filter(
      GeneratedRoom.generated_room_id.like(f"{id_prefix}-%")
      ).order_by(desc(GeneratedRoom.id)).first()
    
    if latest_id_obj: 
      latest_number = int(latest_id_obj[0].split("-")[-1])
      next_generated_room_id = f"{id_prefix}-{latest_number + 1:03d}"
    else:
      next_generated_room_id = f"{id_prefix}-001"

  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Error generating ID: {str(e)}")
    
  # 3. Create GeneratedRoom entry
  design = GeneratedRoom(
    original_image_path=file_path,
    generated_image_path=file_path,
    generated_room_id=next_generated_room_id,
    room_style=room_style,
    design_style=design_style
  )

  db.add(design)
  db.commit()
  db.refresh(design)

  # 4. Filter furniture based on room & style
  furniture_list = db.query(Furniture).filter(
  func.lower(Furniture.room) == design.room_style.lower(),
  func.lower(Furniture.style) == design.design_style.lower()
  ).all()

  if not furniture_list:
    raise HTTPException(status_code=404, detail="No matching furniture found")

  print("Furniture for AI:", [f.name for f in furniture_list])

  # 5. Simulate image generation by copying file 
  src = design.original_image_path
  if not os.path.exists(src):
    raise HTTPException(status_code=400, detail="Original image not found")

  gen_filename = f"generated_{os.path.basename(src)}"
  dest = os.path.join(GENERATED_DIR, gen_filename)
  shutil.copy(src, dest)

  # Update record
  design.generated_image_path = dest
  design.generated_date = datetime.now(timezone.utc)
  db.commit()
  db.refresh(design)

  return design

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
