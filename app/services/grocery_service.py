from fastapi import HTTPException
from sqlmodel import select
from app.models import Grocery
from app.database import get_session

def get_all_groceries():
    with get_session() as session:
        return session.exec(select(Grocery)).all()

def add_grocery(data):
    with get_session() as session:
        existing = session.exec(select(Grocery).where(Grocery.name == data.name)).first()
        if existing:
            raise HTTPException(status_code=400, detail="Item already exists")
        g = Grocery(**data.dict())
        session.add(g)
        session.commit()
        session.refresh(g)
        return g

def update_grocery(item_id, data):
    with get_session() as session:
        g = session.get(Grocery, item_id)
        if not g:
            raise HTTPException(status_code=404, detail="Item not found")
        if data.quantity is not None:
            g.quantity = data.quantity
        if data.threshold is not None:
            g.threshold = data.threshold
        session.add(g)
        session.commit()
        session.refresh(g)
        return g

def delete_grocery(item_id):
    with get_session() as session:
        g = session.get(Grocery, item_id)
        if not g:
            raise HTTPException(status_code=404, detail="Item not found")
        session.delete(g)
        session.commit()
        return True

def get_alerts():
    with get_session() as session:
        groceries = session.exec(select(Grocery)).all()
        return [g for g in groceries if g.quantity < g.threshold]
