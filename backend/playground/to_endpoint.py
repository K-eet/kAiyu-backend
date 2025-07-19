# @router.get("test-function")
# def myfunction():
#    return "hello"

from fastapi import APIRouter
from backend.playground.from_endpoint import myfunction

router = APIRouter() # <--- Add this line

@router.get("/test")
def test_endpoint():
   my_var = myfunction() + "world"
   return my_var