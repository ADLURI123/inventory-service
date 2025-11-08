from fastapi import APIRouter
from typing import List
from app.models import GroceryCreate, GroceryUpdate, Grocery
from app.services import grocery_service

router = APIRouter(prefix="/groceries", tags=["Groceries"])

@router.get("/", response_model=List[Grocery])
def list_groceries():
    return grocery_service.get_all_groceries()

@router.post("/", response_model=Grocery)
def create_grocery(data: GroceryCreate):
    return grocery_service.add_grocery(data)

@router.patch("/{item_id}", response_model=Grocery)
def update_grocery(item_id: int, data: GroceryUpdate):
    return grocery_service.update_grocery(item_id, data)

@router.delete("/{item_id}")
def delete_grocery(item_id: int):
    grocery_service.delete_grocery(item_id)
    return {"deleted": True}

@router.get("/alerts", response_model=List[Grocery])
def alerts():
    return grocery_service.get_alerts()
