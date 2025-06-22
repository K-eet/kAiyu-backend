import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

# Basic setup
app = FastAPI()

# Allow all CORS (you can restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory to store uploaded files
UPLOAD_DIR = "simple_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)  # Ensure directory exists

@app.post("/upload-image/")
async def upload_image(file: UploadFile = File(...)):
    """
    Upload an image file.
    Allowed formats: jpg, jpeg, png.
    Returns filename and file path.
    """
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in [".jpg", ".jpeg", ".png"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Only jpg, jpeg, png allowed.")

    # Unique filename to avoid conflicts
    unique_filename = f"{os.urandom(8).hex()}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"filename": unique_filename, "file_url": f"/view-image/{unique_filename}"}

@app.get("/view-image/{filename}")
async def view_image(filename: str):
    """
    View (serve) the uploaded image by filename.
    """
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(file_path)

@app.get("/")
def root():
    return {"message": "Simple Image Upload & View API. Go to /docs to try it out!"}


