from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.models.models import FurnitureDatabase, GeneratedRoom, FurnitureCoordinates
from backend.schemas.schemas import FurnitureDatabaseModel, FurnitureDatabaseCreate, GeneratedRoomModel, FurnitureCoordinatesModel
from sqlalchemy import func

# --- FurnitureDatabase Router ---
router = APIRouter(prefix="/furniture", tags=["FurnitureDatabase"])

@router.post("/", response_model=FurnitureDatabaseModel)
def add_furniture(furniture: FurnitureDatabaseCreate, db: Session = Depends(get_db)):
	"""
	Add a new furniture item to the database.
	"""
	new_furniture = FurnitureDatabase(**furniture.model_dump(exclude_unset=True))
	db.add(new_furniture)
	db.commit()
	db.refresh(new_furniture)
	return new_furniture

@router.get("/", response_model=List[FurnitureDatabaseModel])
def list_all_furniture(limit: int = 100, offset: int = 0, db: Session = Depends(get_db)):
	"""
	Filter by the item list
	E.g. limit = 10, offset = 0
	"""
	try:
			result = db.query(FurnitureDatabase).offset(offset).limit(limit).all()
			return result
	except Exception as e:
			print("ERROR:", str(e))
			raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.get("/filter", response_model=List[FurnitureDatabaseModel])
def filter_furniture(style: str = Query(None), room: str = Query(None), db: Session = Depends(get_db)):
	"""
	Filter by style and room
	E.g. style: MODERN
				room: LIVING ROOM
	Accept upper and lower case input
	"""
	query = db.query(FurnitureDatabase)
	if style:
			query = query.filter(func.lower(FurnitureDatabase.style) == style.lower())
	if room:
			query = query.filter(func.lower(FurnitureDatabase.room) == room.lower())
	return query.all()

@router.get("/filter-type", response_model=List[FurnitureDatabaseModel])
def filter_furniture_by_type(type: str = Query(None), db: Session = Depends(get_db)):
	"""
	Filter by type of furniture
	E.g. type: BED
	"""
	query = db.query(FurnitureDatabase)
	if type: 
			query = query.filter(func.lower(FurnitureDatabase.type) == type.lower())
	return query.all()

@router.get("/{furniture_id}", response_model=FurnitureDatabaseModel)
def get_furniture_by_id(furniture_id: str, db: Session = Depends(get_db)):
	"""
	Filter by furniture id. 
	E.g. furniture_id: B001 or b001
	Accept upper and lower case input 
	"""
	furniture = db.query(FurnitureDatabase).filter(func.lower(FurnitureDatabase.furniture_id) == furniture_id.lower()).first()
	if not furniture:
			raise HTTPException(status_code=404, detail="FurnitureDatabase not found")
	return furniture

@router.put("/{furniture_id}", response_model=FurnitureDatabaseModel)
def update_furniture(furniture_id: int, updated: FurnitureDatabaseModel, db: Session = Depends(get_db)):
	"""
	Optional:
	Update furniture item
	"""
	furniture = db.query(FurnitureDatabase).filter_by(id=furniture_id).first()
	if not furniture:
			raise HTTPException(status_code=404, detail="FurnitureDatabase not found")

	for key, value in updated.dict(exclude_unset=True).items():
			setattr(furniture, key, value)

	db.commit()
	db.refresh(furniture)
	return furniture

@router.delete("/{furniture_id}", response_model=dict)
def delete_furniture(furniture_id: int, db: Session = Depends(get_db)):
	"""
	Optional: 
	Delete furniture item
	"""
	furniture = db.query(FurnitureDatabase).filter_by(id=furniture_id).first()
	if not furniture:
			raise HTTPException(status_code=404, detail="FurnitureDatabase not found")
	db.delete(furniture)
	db.commit()
	return {"message": f"FurnitureDatabase with ID {furniture_id} deleted."}
