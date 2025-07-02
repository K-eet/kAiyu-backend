import base64
from sqlalchemy import create_engine, Column, Integer, String, Double, Text
from sqlalchemy.orm import sessionmaker, declarative_base
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.responses import Response
from typing import Dict, Optional
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend.models.models import Furniture

DB_USER = "postgres"
DB_PASSWORD = "password"
DB_HOST = "localhost"
DB_NAME = "books_db"
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"

engine = create_engine(DATABASE_URL)
Base = declarative_base()

SessionLocal = sessionmaker(bind=engine)


class inputimage(Base):
    __tablename__ = "imginput"
    id = Column(Integer, primary_key=True, autoincrement=True)
    image = Column(Text, nullable=False)
    room_type = Column(String, nullable=False)
    room_style = Column(String, nullable=False)


Base.metadata.create_all(engine)


class inputimageModel(BaseModel):
    image: Optional[str] = None
    room_type: Optional[str] = None
    room_style: Optional[str] = None


app = FastAPI()

# Database dependency


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def encode_image(image_content: bytes) -> str:
    return base64.b64encode(image_content).decode()


def decode_image(image_content_in: str) -> bytes:
    return base64.b64decode(image_content_in)


@app.post("/upload-emptyroom")
async def upload_image(
    file: UploadFile = File(...),
    db: SessionLocal = Depends(get_db)
) -> Dict[str, str]:
    if file.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(400, detail="Invalid file type")

    if file.size and file.size > 10_000_000:
        raise HTTPException(400, detail="File too large")

    # Read the file content
    image_content = await file.read()

    # Encode to base64
    base64_image = encode_image(image_content)

    # Save to database
    db_image = inputimage(image=base64_image)
    db.add(db_image)
    db.commit()
    db.refresh(db_image)

    # Return the response
    return {
        "message": "Image uploaded successfully",
        "image_id": str(db_image.id),
        "base64_image": base64_image
    }


@app.get("/images/{image_id}")
async def get_image(
    db: SessionLocal = Depends(get_db)
):
    """Get and display image - viewable in Swagger UI"""
    image = db.query(inputimage).order_by(inputimage.id.desc()).first()

    if not image:
        raise HTTPException(404, detail="Image not found")

    # Decode base64 back to image bytes
    image_bytes = decode_image(image.image)

    # Detect content type based on image header
    content_type = "image/jpeg"  # default
    if image_bytes.startswith(b'\x89PNG'):
        content_type = "image/png"

    # Return as image response that Swagger UI can display
    return Response(
        content=image_bytes,
        media_type=content_type,
        headers={"Content-Disposition": "inline"}
    )


@app.get("/furniture")
async def get_furniture(room: Optional[str] = None, style: Optional[str] = None):

    furniture_list = Furniture

    if room:
        furniture_list = [item for item in furniture_list["room"] == room]

    if style:
        furniture_list = [item for item in furniture_list["style"] == style]

    return furniture_list


@app.post("/generate_room")
async def generated_room(
    request: inputimageModel,
    db: SessionLocal = Depends(get_db)
):
    try:
        image = db.query(inputimage).order_by(inputimage.id.desc()).first()

        if not image:
            raise HTTPException(404, detail="Image not found")

        # Decode base64 back to image bytes
        image_bytes = decode_image(image.image)
        # AI process should be writen here

        generated_room_url = {("bedroom", "modern"): "link here"}

        generated_room_image = generated_room_url.get((request.room_type, request.room_style),
                                                    "link")

        furniture_items = [
            item for item in Furniture
            if item["room"] == request.room_type and item["style"] == request.room_style
    ]

        return {

        "generated_room_image": generated_room_image,
        "furniture_items": furniture_items,
        "success": True
    }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"gen fial:{str(e)}")
