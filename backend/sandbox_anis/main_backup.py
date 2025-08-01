from fastapi import FastAPI
from contextlib import asynccontextmanager
from backend.core.database import Base, engine
from backend.playground import to_endpoint
from backend.routers import furniture, generated, coordinates
from backend.services.similarity import similarity_service # Import the service
from backend.routers import coordinates, generated # Make sure all your routers are imported
from fastapi.middleware.cors import CORSMiddleware

# The catalog URL you provided
CATALOG_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQjHECrs5aRM3RcWdf2hqMKa05n3GKgPhLLWLWpdhpghXGtl6VTy0XuVq8V2CnvC99umfpXProkfEWX/pub?gid=86375611&single=true&output=csv"

@asynccontextmanager
async def lifespan(app: FastAPI):
  Base.metadata.create_all(bind=engine)
  # Load the ML model and catalog
  print("Application startup: Loading models and catalog...")
  similarity_service.load_and_process_catalog(CATALOG_URL)
  print("Models and catalog loaded successfully.")
  yield
  # Clean up the ML models and release the resources
  print("Application shutdown: Cleaning up...")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
  )

app.include_router(furniture.router)
app.include_router(generated.router)
app.include_router(coordinates.router)

@app.get("/")
def read_root():
  return {"message": "Welcome to the Furniture API"}