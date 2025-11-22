from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

DB_DIR = "/database"
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "grocery.db")

app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

class Grocery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    stock = db.Column(db.Integer, default=0)
    threshold = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "stock": self.stock,
            "threshold": self.threshold,
            "created_at": self.created_at.isoformat()
        }

class StockMovement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    grocery_id = db.Column(db.Integer, db.ForeignKey("grocery.id"), nullable=False)
    change = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "grocery_id": self.grocery_id,
            "change": self.change,
            "created_at": self.created_at.isoformat()
        }

with app.app_context():
    db.create_all()

@app.route("/grocery", methods=["POST"])
def create_grocery():
    data = request.json or {}
    name = data.get("name", "").strip()
    threshold = int(data.get("threshold", 0))
    if not name:
        return jsonify({"error": "Name required"}), 400
    if Grocery.query.filter_by(name=name).first():
        return jsonify({"error": "Grocery exists"}), 400
    g = Grocery(name=name, threshold=threshold, stock=int(data.get("stock", 0)))
    db.session.add(g)
    db.session.commit()
    return jsonify({"message": "Created", "data": g.to_dict()}), 201

@app.route("/groceries", methods=["GET"])
def list_groceries():
    groceries = Grocery.query.order_by(Grocery.created_at.desc()).all()
    return jsonify([g.to_dict() for g in groceries])

@app.route("/grocery/<int:g_id>", methods=["GET"])
def get_grocery(g_id):
    g = Grocery.query.get(g_id)
    if not g:
        return jsonify({"error": "Not found"}), 404
    return jsonify(g.to_dict())

@app.route("/grocery/<int:g_id>", methods=["PUT"])
def update_grocery(g_id):
    g = Grocery.query.get(g_id)
    if not g:
        return jsonify({"error": "Not found"}), 404
    data = request.json or {}
    if "name" in data:
        new_name = data["name"].strip()
        if new_name != g.name:
            if Grocery.query.filter_by(name=new_name).first():
                return jsonify({"error": "Name exists"}), 400
            g.name = new_name
    if "threshold" in data:
        g.threshold = int(data["threshold"])
    if "stock" in data:
        g.stock = max(0, int(data["stock"]))
    db.session.commit()
    return jsonify({"message": "Updated", "data": g.to_dict()})

@app.route("/grocery/<int:g_id>", methods=["DELETE"])
def delete_grocery(g_id):
    g = Grocery.query.get(g_id)
    if not g:
        return jsonify({"error": "Not found"}), 404
    db.session.delete(g)
    db.session.commit()
    return jsonify({"message": "Deleted"})

@app.route("/grocery/<int:g_id>/add", methods=["POST"])
def add_stock(g_id):
    g = Grocery.query.get(g_id)
    if not g:
        return jsonify({"error": "Not found"}), 404
    qty = int((request.json or {}).get("qty", 0))
    if qty <= 0:
        return jsonify({"error": "Invalid qty"}), 400
    g.stock += qty
    mov = StockMovement(grocery_id=g.id, change=qty)
    db.session.add(mov)
    db.session.commit()
    return jsonify({"message": "Added", "data": g.to_dict()})

@app.route("/grocery/<int:g_id>/subtract", methods=["POST"])
def subtract_stock(g_id):
    g = Grocery.query.get(g_id)
    if not g:
        return jsonify({"error": "Not found"}), 404
    qty = int((request.json or {}).get("qty", 0))
    if qty <= 0:
        return jsonify({"error": "Invalid qty"}), 400
    g.stock = max(0, g.stock - qty)
    mov = StockMovement(grocery_id=g.id, change=-qty)
    db.session.add(mov)
    db.session.commit()
    return jsonify({"message": "Subtracted", "data": g.to_dict()})

@app.route("/alerts", methods=["GET"])
def low_stock_alerts():
    lows = Grocery.query.filter(Grocery.stock < Grocery.threshold).all()
    return jsonify([g.to_dict() for g in lows])

@app.route("/stats/summary", methods=["GET"])
def stats_summary():
    groceries = Grocery.query.all()
    total_items = len(groceries)
    low_items = len([g for g in groceries if g.stock < g.threshold])
    total_stock = sum(g.stock for g in groceries)
    return jsonify({
        "total_items": total_items,
        "low_items": low_items,
        "total_stock": total_stock,
        "items": [g.to_dict() for g in groceries]
    })

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
