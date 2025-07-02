import os
import shutil
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Form
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from backend.core.config import UPLOAD_DIR, GENERATED_DIR
from backend.core.database import get_db
from backend.models.models import Furniture, GeneratedRoom, FurnitureCoordinates
from backend.schemas.schemas import FurnitureCreate, FurnitureModel, GeneratedRoomModel, FurnitureCoordinatesModel
import uuid

router = APIRouter(prefix="/generated", tags=["Generated Rooms"])

@router.post("/upload-select-room-style/", response_model=GeneratedRoomModel)
def upload_image(
    file: UploadFile = File(... ),
    room_style: str = Form(..., description="e.g. Bedroom, Living Room"),   # Dropdown selection from frontend
    design_style: str = Form(..., description="e.g. Modern, Scandinavian"), # Chip button style selection
    db: Session = Depends(get_db)
):
    """
    User need to upload selected picture in either [.jpg, .jpeg or .png] format and 
    need to input the room style and design style 
    E.g. room_style: Bedroom
         design_style: Modern
    """
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png"]:
        raise HTTPException(status_code=400, detail="Invalid file type")

    filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Get the current max generated_room_id
    latest = db.query(func.max(GeneratedRoom.generated_room_id)).scalar()
    next_generated_room_id = 1 if latest is None else latest + 1

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
    return design

@router.post("/generate/{room_id}", response_model=GeneratedRoomModel)
def generate_image(room_id: int, db: Session = Depends(get_db)):
    """
    A temporary placeholder for the generate AI button function
    This POST endpoint function will generate the image and will give the generated_image_path
    """
    design = db.query(GeneratedRoom).filter_by(generated_room_id=room_id).first()
    if not design:
        raise HTTPException(status_code=404, detail="GeneratedRoom not found")

    src = design.original_image_path
    if not os.path.exists(src):
        raise HTTPException(status_code=400, detail="Original image not found")

    filename = f"generated_{os.path.basename(src)}"
    dest = os.path.join(GENERATED_DIR, filename)
    shutil.copy(src, dest)

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


# @router.post("/upload/", response_model=GeneratedRoomModel)
# def upload_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
#     ext = os.path.splitext(file.filename)[1].lower()
#     if ext not in [".jpg", ".jpeg", ".png"]:
#         raise HTTPException(status_code=400, detail="Invalid file type")

#     # filename = f"{os.urandom(8).hex()}{ext}"
#     filename = f"{uuid.uuid4().hex}{ext}"
#     file_path = os.path.join(UPLOAD_DIR, filename)

#     with open(file_path, "wb") as buffer:
#         shutil.copyfileobj(file.file, buffer)
    
#     # Get the current max generated_room_id
#     latest = db.query(func.max(GeneratedRoom.generated_room_id)).scalar()
#     next_generated_room_id = 1 if latest is None else latest + 1

#     design = GeneratedRoom(
#         original_image_path=file_path,
#         generated_image_path=file_path,
#         generated_room_id=next_generated_room_id,
#         room_style="unknown",
#         design_style="original"
#     )

#     db.add(design)
#     db.commit()
#     db.refresh(design)
#     return design

# @router.post("/upload/{furniture_id}", response_model=GeneratedRoomModel)
# def upload_image(furniture_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
#     furniture = db.query(Furniture).filter_by(id=furniture_id).first()
#     if not furniture:
#         raise HTTPException(status_code=404, detail="Furniture not found")

#     ext = os.path.splitext(file.filename)[1].lower()
#     if ext not in [".jpg", ".jpeg", ".png"]:
#         raise HTTPException(status_code=400, detail="Invalid file type")

#     filename = f"{furniture_id}_{os.urandom(8).hex()}{ext}"
#     file_path = os.path.join(UPLOAD_DIR, filename)

#     with open(file_path, "wb") as buffer:
#         shutil.copyfileobj(file.file, buffer)

#     design = GeneratedRoom(
#         furniture_id=furniture_id,
#         original_image_path=file_path,
#         generated_image_path=file_path,
#         design_style="original"
#     )
#     db.add(design)
#     db.commit()
#     db.refresh(design)
#     return design