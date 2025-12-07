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
    unit_cost = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "stock": self.stock,
            "threshold": self.threshold,
            "unit_cost": self.unit_cost,
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

class Food(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), unique=True, nullable=False)
    selling_price = db.Column(db.Float, default=0.0)
    cost_price = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self, include_groceries=False):
        d = {
            "id": self.id,
            "name": self.name,
            "selling_price": self.selling_price,
            "cost_price": self.cost_price,
            "profit": self.selling_price - self.cost_price,
            "margin_percent": ((self.selling_price - self.cost_price) / self.selling_price * 100) if self.selling_price else 0,
            "created_at": self.created_at.isoformat()
        }
        if include_groceries:
            recs = FoodRecipe.query.filter_by(food_id=self.id).all()
            d["groceries"] = [
                {
                    "grocery_id": r.grocery_id,
                    "grocery_name": r.grocery.name if r.grocery else None,
                    "quantity": r.quantity,
                    "unit_cost": r.grocery.unit_cost if r.grocery else 0,
                    "line_cost": r.quantity * (r.grocery.unit_cost if r.grocery else 0)
                }
                for r in recs
            ]
        return d

class FoodRecipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    food_id = db.Column(db.Integer, db.ForeignKey("food.id"), nullable=False)
    grocery_id = db.Column(db.Integer, db.ForeignKey("grocery.id"), nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=0.0)
    grocery = db.relationship("Grocery", lazy="joined")

with app.app_context():
    db.create_all()

def compute_food_cost(food_id):
    recs = FoodRecipe.query.filter_by(food_id=food_id).all()
    total = 0.0
    for r in recs:
        if r.grocery and r.grocery.unit_cost:
            total += r.quantity * r.grocery.unit_cost
    food = Food.query.get(food_id)
    if food:
        food.cost_price = total
        db.session.commit()
    return total

@app.route("/grocery", methods=["POST"])
def create_grocery():
    data = request.json or {}
    name = data.get("name", "").strip()
    threshold = int(data.get("threshold", 0))
    stock = int(data.get("stock", 0))
    unit_cost = float(data.get("unit_cost", 0.0))
    if not name:
        return jsonify({"error": "Name required"}), 400
    if Grocery.query.filter_by(name=name).first():
        return jsonify({"error": "Grocery exists"}), 400
    g = Grocery(name=name, threshold=threshold, stock=stock, unit_cost=unit_cost)
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
    if "unit_cost" in data:
        g.unit_cost = float(data["unit_cost"])
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
    db.session.add(StockMovement(grocery_id=g.id, change=qty))
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
    db.session.add(StockMovement(grocery_id=g.id, change=-qty))
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
    return jsonify({
        "total_items": total_items,
        "low_items": low_items,
        "in_stock": total_items - low_items,
        "items": [g.to_dict() for g in groceries]
    })

@app.route("/food", methods=["POST"])
def create_food():
    data = request.json or {}
    name = data.get("name", "").strip()
    selling_price = float(data.get("selling_price", 0.0))
    groceries_data = data.get("groceries", [])
    if not name:
        return jsonify({"error": "Name required"}), 400
    if Food.query.filter_by(name=name).first():
        return jsonify({"error": "Food exists"}), 400
    food = Food(name=name, selling_price=selling_price)
    db.session.add(food)
    db.session.commit()
    for item in groceries_data:
        g_id = int(item.get("grocery_id") or item.get("id"))
        qty = float(item.get("quantity", 0.0))
        if qty <= 0:
            continue
        if Grocery.query.get(g_id):
            db.session.add(FoodRecipe(food_id=food.id, grocery_id=g_id, quantity=qty))
    db.session.commit()
    compute_food_cost(food.id)
    return jsonify({"message": "Created", "data": food.to_dict(include_groceries=True)}), 201

@app.route("/foods", methods=["GET"])
def list_foods():
    foods = Food.query.order_by(Food.created_at.desc()).all()
    return jsonify([f.to_dict(include_groceries=True) for f in foods])

@app.route("/food/<int:f_id>", methods=["GET"])
def get_food(f_id):
    f = Food.query.get(f_id)
    if not f:
        return jsonify({"error": "Not found"}), 404
    return jsonify(f.to_dict(include_groceries=True))

@app.route("/food/<int:f_id>", methods=["PUT"])
def update_food(f_id):
    f = Food.query.get(f_id)
    if not f:
        return jsonify({"error": "Not found"}), 404
    data = request.json or {}
    if "name" in data:
        new_name = data["name"].strip()
        if new_name != f.name:
            if Food.query.filter_by(name=new_name).first():
                return jsonify({"error": "Food exists"}), 400
            f.name = new_name
    if "selling_price" in data:
        f.selling_price = float(data["selling_price"])
    db.session.commit()
    if "groceries" in data:
        FoodRecipe.query.filter_by(food_id=f.id).delete()
        db.session.commit()
        for item in data["groceries"]:
            g_id = int(item.get("grocery_id") or item.get("id"))
            qty = float(item.get("quantity", 0.0))
            if qty <= 0:
                continue
            if Grocery.query.get(g_id):
                db.session.add(FoodRecipe(food_id=f.id, grocery_id=g_id, quantity=qty))
        db.session.commit()
        compute_food_cost(f.id)
    else:
        compute_food_cost(f.id)
    return jsonify({"message": "Updated", "data": f.to_dict(include_groceries=True)})

@app.route("/food/<int:f_id>", methods=["DELETE"])
def delete_food(f_id):
    f = Food.query.get(f_id)
    if not f:
        return jsonify({"error": "Not found"}), 404
    FoodRecipe.query.filter_by(food_id=f.id).delete()
    db.session.delete(f)
    db.session.commit()
    return jsonify({"message": "Deleted"})

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
