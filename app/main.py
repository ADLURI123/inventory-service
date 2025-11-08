from fastapi import FastAPI
from app.database import init_db
from app.routers import groceries

app = FastAPI(title="Hotel Grocery Inventory")

@app.on_event("startup")
def startup_event():
    init_db()

app.include_router(groceries.router)