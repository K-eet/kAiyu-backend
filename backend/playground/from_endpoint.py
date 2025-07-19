from fastapi import APIRouter

router = APIRouter()

@router.get("/test-function")
def myfunction():
   return "hello"