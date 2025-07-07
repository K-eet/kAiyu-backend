from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timezone
from backend.core.database import get_db
from backend.models.models import GeneratedRoom, Furniture
from backend.schemas.schemas import GeneratedRoomModel
import os, shutil, uuid, re
from fastapi.responses import FileResponse
from typing import List

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
  # Validate file
  ext = os.path.splitext(file.filename)[1].lower()
  if ext not in [".jpg", ".jpeg", ".png"]:
      raise HTTPException(status_code=400, detail="Invalid file type")

  filename = f"{uuid.uuid4().hex}{ext}"
  file_path = os.path.join(UPLOAD_DIR, filename)

  with open(file_path, "wb") as buffer:
      shutil.copyfileobj(file.file, buffer)

  # Generate custom room ID
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

  # Initial DB record
  design = GeneratedRoom(
      original_image_path=file_path,
      generated_image_path="",
      generated_room_id=next_generated_room_id,
      room_style=room_style,
      design_style=design_style
  )
  db.add(design)
  db.commit()
  db.refresh(design)

  # Generate image with Stable Diffusion
  try:
      input_image = Image.open(file_path).convert("RGB")
      if input_image.size != (512, 512):
          input_image = input_image.resize((512, 512))

      prompt = f"Decorate this {room_style.lower()} with {design_style.lower()} furniture, clean, modern and aesthetic"
      generated = pipe(
          prompt=prompt,
          image=input_image,
          strength=0.75,
          guidance_scale=7.5
      ).images[0]

      # Save generated image
      gen_filename = f"generated_{filename}"
      dest = os.path.join(GENERATED_DIR, gen_filename)
      generated.save(dest)

      # Update DB
      design.generated_image_path = dest
      design.generated_date = datetime.now(timezone.utc)
      db.commit()
      db.refresh(design)

      return design

  except Exception as e:
      raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")

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
