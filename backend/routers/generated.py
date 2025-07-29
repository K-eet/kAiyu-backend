from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Response
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime, timezone
from backend.core.database import get_db
from backend.models.models import GeneratedRoom
from backend.schemas.schemas import GeneratedRoomModel
import os, shutil, uuid
from fastapi.responses import FileResponse
from typing import List

# --- AI Model Imports ---
from diffusers import StableDiffusionImg2ImgPipeline, AutoPipelineForImage2Image
import torch
from PIL import Image

# Assuming you have a config file for directories
# from backend.core.config import UPLOAD_DIR, GENERATED_DIR
# If not, define them here:
UPLOAD_DIR = "uploads"
GENERATED_DIR = "generated"

router = APIRouter(prefix="/generated", tags=["Generated Rooms"])

# --- MODEL LOADING ---
# Load the correct base model for image-to-image tasks once on startup.
device = "cuda" if torch.cuda.is_available() else "cpu"

pipe = AutoPipelineForImage2Image.from_pretrained(
  "stabilityai/stable-diffusion-xl-refiner-1.0",
  torch_dtype=torch.float16 if device == "cuda" else torch.float32,
  variant="fp16",
  use_safetensors=True
).to(device)
print("Stable Diffusion XL Base model loaded successfully.")


@router.post("/generate-image/", response_model=GeneratedRoomModel)
def upload_and_generate_image(
  file: UploadFile = File(..., description="Upload empty room"),
  room_style: str = Form(..., description="e.g. Bedroom, Living Room"),
  design_style: str = Form(..., description="e.g. Modern, Scandinavian"),
  db: Session = Depends(get_db)
):
  """
  Uploads an empty room image, generates a new furnished image using Stable Diffusion,
  and saves a single, complete record to the database.
  
  Workflow:
  1. Validate the uploaded image format (jpg, jpeg, png).
  2. Save the uploaded image locally to the 'uploads' directory.
  3. Generate a unique `generated_room_id` (R-YYMMDD-###) for the room.
  4. Create an initial database record for the uploaded image with room type and design style.
  5. Process the uploaded image using the Stable Diffusion XL Refiner pipeline:
     - Resize image to 1280x720 for consistency.
     - Apply text-to-image prompt to generate a realistic, aesthetic furnished version.
     - Save the generated image to the 'generated' directory.
  6. Update the database with the generated image path and timestamp.
  7. Return the updated database record as API response.

  Raises:
      400: Invalid file type.
      404: Image file not found.
      500: Database ID generation or image generation failure.
  """
  # --- 1. FILE VALIDATION AND SAVING ---
  ext = os.path.splitext(file.filename)[1].lower()
  if ext not in [".jpg", ".jpeg", ".png"]:
    raise HTTPException(status_code=400, detail="Invalid file type. Please use jpg, jpeg, or png.")

  filename = f"{uuid.uuid4().hex}{ext}"
  original_file_path = os.path.join(UPLOAD_DIR, filename)

  try:
    with open(original_file_path, "wb") as buffer:
      shutil.copyfileobj(file.file, buffer)
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {e}")

  # --- 2. AI IMAGE GENERATION ---
  try:
    print(f"Starting image generation for: {original_file_path}")
    input_image = Image.open(original_file_path).convert("RGB")
    
    if input_image.size != (1280, 720):
         input_image = input_image.resize((1280, 720))

    prompt = f"""You are an interior designer. Decorate this {room_style.lower()} with {design_style.lower()} IKEA furniture, clean, soft natural light, aesthetic, realistic without changing or any features, dimensions, perspective and layout of the original room. DO NOT duplicate furniture. DO NOT generate in low quality, distorted, messy, dark, and cluttered. Your first priority would be furniture detection.
    """
    
    generated_image = pipe(
      prompt=prompt, image=input_image,
      strength=0.75, guidance_scale=8.0
    ).images[0]

    # Save the generated image
    gen_filename = f"generated_{filename}"
    generated_file_path = os.path.join(GENERATED_DIR, gen_filename)
    generated_image.save(generated_file_path)
    print(f"Generated image saved to: {generated_file_path}")

  except Exception as e:
    # If generation fails, we don't proceed, so no DB record is created.
    raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")

  # --- 3. DATABASE RECORD CREATION (AFTER SUCCESSFUL GENERATION) ---
  # This block now runs ONLY if the AI generation was successful.
  try:
    # Generate a unique ID for the new room
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

    # Create the complete database record now
    design = GeneratedRoom(
      generated_room_id=next_generated_room_id,
      room_style=room_style,
      design_style=design_style,
      original_image_path=original_file_path,
      generated_image_path=generated_file_path, # Use the path of the saved generated image
      generated_date=datetime.now(timezone.utc)
    )
    db.add(design)
    db.commit()
    db.refresh(design)

    return design
  except Exception as e:
    raise HTTPException(status_code=500, detail=f"Failed to save record to database: {str(e)}")


@router.get("/view/{folder}/{filename}")
def view_image(folder: str, filename: str, response: Response):
  """Serves an image from the 'uploads' or 'generated' directory."""
  print("Input data: ", folder, filename)

  VALID_FOLDERS = {"uploads": UPLOAD_DIR, "generated": GENERATED_DIR}
  print("Expected data: ", VALID_FOLDERS)
  
  if folder not in VALID_FOLDERS:
    print(folder, filename)
    raise HTTPException(status_code=404, detail="Folder not found.")

  path = os.path.join(VALID_FOLDERS[folder], filename)
  if not os.path.exists(path):
    raise HTTPException(status_code=404, detail="Image not found.")

  # Add CORS headers manually
  response.headers["Access-Control-Allow-Origin"] = "*"
  response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
  response.headers["Access-Control-Allow-Headers"] = "*"
  response.headers["Access-Control-Allow-Credentials"] = "true"

  return FileResponse(path, media_type="image/jpeg", headers=response.headers)


@router.get("/gallery", response_model=List[GeneratedRoomModel])
def get_all_generated_rooms(db: Session = Depends(get_db)):
  """Gets all generated room records for the gallery view."""
  rooms = db.query(GeneratedRoom).order_by(desc(GeneratedRoom.generated_date)).all()
  return rooms