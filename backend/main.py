from fastapi import FastAPI
from contextlib import asynccontextmanager
from backend.core.database import Base, engine
from backend.routers import furniture, generated
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

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

@app.get("/")
def read_root():
    return {"message": "Welcome to the Furniture API"}