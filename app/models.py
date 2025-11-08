from sqlmodel import SQLModel, Field
from typing import Optional

class GroceryBase(SQLModel):
    name: str
    threshold: float
    quantity: float = 0.0
    unit: str = "pcs"

class Grocery(GroceryBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

class GroceryCreate(GroceryBase):
    pass

class GroceryUpdate(SQLModel):
    quantity: Optional[float] = None
    threshold: Optional[float] = None