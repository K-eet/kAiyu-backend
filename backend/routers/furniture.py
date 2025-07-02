from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.models.models import Furniture, GeneratedRoom, FurnitureCoordinates
from backend.schemas.schemas import FurnitureModel, FurnitureCreate, GeneratedRoomModel, FurnitureCoordinatesModel
from sqlalchemy import func

# --- Furniture Router ---
router = APIRouter(prefix="/furniture", tags=["Furniture"])

@router.post("/", response_model=FurnitureModel)
def add_furniture(furniture: FurnitureCreate, db: Session = Depends(get_db)):
  """
  Add a new furniture item to the database.
  """
  new_furniture = Furniture(**furniture.model_dump(exclude_unset=True))
  db.add(new_furniture)
  db.commit()
  db.refresh(new_furniture)
  return new_furniture

@router.get("/", response_model=List[FurnitureModel])
def list_all_furniture(limit: int = 100, offset: int = 0, db: Session = Depends(get_db)):
    """
    Filter by the item list
    E.g. limit = 10, offset = 0
    """
    try:
        result = db.query(Furniture).offset(offset).limit(limit).all()
        return result
    except Exception as e:
        print("ERROR:", str(e))
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.get("/filter", response_model=List[FurnitureModel])
def filter_furniture(style: str = Query(None), room: str = Query(None), db: Session = Depends(get_db)):
    """
    Filter by style and room
    E.g. style = MODERN
         room = LIVING ROOM
    """
    query = db.query(Furniture)
    if style:
        query = query.filter(func.lower(Furniture.style) == style.lower())
    if room:
        query = query.filter(func.lower(Furniture.room) == room.lower())
    return query.all()

@router.get("/filter-type", response_model=List[FurnitureModel])
def filter_furniture_by_type(type: str = Query(None), db: Session = Depends(get_db)):
    """
    Filter by type of furniture
    E.g. type = BED
    """
    query = db.query(Furniture)
    if type: 
        query = query.filter(func.lower(Furniture.type) == type.lower())
    return query.all()

@router.get("/{furniture_id}", response_model=FurnitureModel)
def get_furniture_by_id(furniture_id: str, db: Session = Depends(get_db)):
    """
    Filter by furniture id. Can accept lowercase
    E.g. furniture_id = B001 or b001
    """
    furniture = db.query(Furniture).filter(func.lower(Furniture.furniture_id) == furniture_id.lower()).first()
    if not furniture:
        raise HTTPException(status_code=404, detail="Furniture not found")
    return furniture

@router.put("/{furniture_id}", response_model=FurnitureModel)
def update_furniture(furniture_id: int, updated: FurnitureModel, db: Session = Depends(get_db)):
    """
    Update furniture item
    """
    furniture = db.query(Furniture).filter_by(id=furniture_id).first()
    if not furniture:
        raise HTTPException(status_code=404, detail="Furniture not found")

    for key, value in updated.dict(exclude_unset=True).items():
        setattr(furniture, key, value)

    db.commit()
    db.refresh(furniture)
    return furniture

@router.delete("/{furniture_id}", response_model=dict)
def delete_furniture(furniture_id: int, db: Session = Depends(get_db)):
    """
    Delete furniture item
    """
    furniture = db.query(Furniture).filter_by(id=furniture_id).first()
    if not furniture:
        raise HTTPException(status_code=404, detail="Furniture not found")
    db.delete(furniture)
    db.commit()
    return {"message": f"Furniture with ID {furniture_id} deleted."}
