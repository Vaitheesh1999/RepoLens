"""Messy FastAPI application - intentionally problematic."""

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
import json
from datetime import datetime
from utils import sanitize_string, calculate_hash, get_timestamp
from models_helper import User, Product
from database import get_db_connection, init_database

app = FastAPI()


class UserSchema(BaseModel):
    """User schema."""
    email: str
    password: str
    name: Optional[str] = None


class ProductSchema(BaseModel):
    """Product schema."""
    name: str
    price: float
    stock: int


class OrderSchema(BaseModel):
    """Order schema."""
    user_id: int
    product_id: int
    quantity: int


# === DUPLICATE: These functions are also in utils.py ===

def sanitize_string(text):
    """Remove special characters from string."""
    if not text:
        return ""
    return "".join(c for c in text if c.isalnum() or c.isspace())


def calculate_hash(text):
    """Calculate simple hash of text."""
    hash_val = 0
    for char in text:
        hash_val = (hash_val * 31 + ord(char)) % (2 ** 32)
    return hash_val


def get_timestamp():
    """Get current timestamp."""
    return datetime.now().isoformat()


# === Database operations mixed with routes ===

def create_user_in_db(email, password, name):
    """Create user directly in database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    hashed_pw = calculate_hash(password)
    cursor.execute(
        "INSERT INTO users (email, password, name) VALUES (?, ?, ?)",
        (sanitize_string(email), hashed_pw, sanitize_string(name))
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return user_id


def get_user_from_db(user_id):
    """Get user from database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, name FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result


def update_user_in_db(user_id, name, email):
    """Update user in database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET name = ?, email = ? WHERE id = ?",
        (sanitize_string(name), sanitize_string(email), user_id)
    )
    conn.commit()
    conn.close()


def delete_user_from_db(user_id):
    """Delete user from database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


def get_all_users_from_db():
    """Get all users from database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, name FROM users")
    results = cursor.fetchall()
    conn.close()
    return results


def create_product_in_db(name, price, stock):
    """Create product in database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO products (name, price, stock) VALUES (?, ?, ?)",
        (sanitize_string(name), price, stock)
    )
    conn.commit()
    product_id = cursor.lastrowid
    conn.close()
    return product_id


def get_product_from_db(product_id):
    """Get product from database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price, stock FROM products WHERE id = ?", (product_id,))
    result = cursor.fetchone()
    conn.close()
    return result


def update_product_in_db(product_id, name, price, stock):
    """Update product in database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE products SET name = ?, price = ?, stock = ? WHERE id = ?",
        (sanitize_string(name), price, stock, product_id)
    )
    conn.commit()
    conn.close()


def create_order_in_db(user_id, product_id, quantity):
    """Create order in database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO orders (user_id, product_id, quantity, created_at) VALUES (?, ?, ?, ?)",
        (user_id, product_id, quantity, get_timestamp())
    )
    conn.commit()
    order_id = cursor.lastrowid
    conn.close()
    return order_id


def get_order_from_db(order_id):
    """Get order from database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, user_id, product_id, quantity, created_at FROM orders WHERE id = ?",
        (order_id,)
    )
    result = cursor.fetchone()
    conn.close()
    return result


def get_user_orders_from_db(user_id):
    """Get all orders for user from database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, user_id, product_id, quantity, created_at FROM orders WHERE user_id = ?",
        (user_id,)
    )
    results = cursor.fetchall()
    conn.close()
    return results


# === Route handlers mixed in same file ===

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    init_database()


@app.post("/users")
async def create_user(user: UserSchema):
    """Create new user - DB operation inline in route."""
    email = sanitize_string(user.email)
    name = sanitize_string(user.name or user.email.split("@")[0])
    
    user_id = create_user_in_db(email, user.password, name)
    
    return {"user_id": user_id, "email": email, "name": name}


@app.get("/users/{user_id}")
async def get_user(user_id: int):
    """Get user by ID."""
    user = get_user_from_db(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user[0], "email": user[1], "name": user[2]}


@app.put("/users/{user_id}")
async def update_user(user_id: int, data: UserSchema):
    """Update user."""
    user = get_user_from_db(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_user_in_db(user_id, data.name or user[2], data.email)
    return {"message": "User updated", "user_id": user_id}


@app.delete("/users/{user_id}")
async def delete_user(user_id: int):
    """Delete user."""
    user = get_user_from_db(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    delete_user_from_db(user_id)
    return {"message": "User deleted"}


@app.get("/users")
async def list_users():
    """List all users."""
    users = get_all_users_from_db()
    return {"users": [{"id": u[0], "email": u[1], "name": u[2]} for u in users]}


@app.post("/products")
async def create_product(product: ProductSchema):
    """Create new product."""
    product_id = create_product_in_db(product.name, product.price, product.stock)
    return {"product_id": product_id, "name": product.name, "price": product.price}


@app.get("/products/{product_id}")
async def get_product(product_id: int):
    """Get product by ID."""
    product = get_product_from_db(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"id": product[0], "name": product[1], "price": product[2], "stock": product[3]}


@app.put("/products/{product_id}")
async def update_product(product_id: int, product: ProductSchema):
    """Update product."""
    existing = get_product_from_db(product_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")
    
    update_product_in_db(product_id, product.name, product.price, product.stock)
    return {"message": "Product updated", "product_id": product_id}


@app.post("/orders")
async def create_order(order: OrderSchema):
    """Create new order - mixing DB and business logic."""
    user = get_user_from_db(order.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    product = get_product_from_db(order.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if order.quantity > product[3]:
        raise HTTPException(status_code=400, detail="Insufficient stock")
    
    order_id = create_order_in_db(order.user_id, order.product_id, order.quantity)
    
    new_stock = product[3] - order.quantity
    update_product_in_db(order.product_id, product[1], product[2], new_stock)
    
    return {"order_id": order_id, "status": "created"}


@app.get("/orders/{order_id}")
async def get_order(order_id: int):
    """Get order by ID."""
    order = get_order_from_db(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {
        "id": order[0],
        "user_id": order[1],
        "product_id": order[2],
        "quantity": order[3],
        "created_at": order[4],
    }


@app.get("/users/{user_id}/orders")
async def get_user_orders(user_id: int):
    """Get all orders for user."""
    user = get_user_from_db(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    orders = get_user_orders_from_db(user_id)
    return {
        "user_id": user_id,
        "orders": [
            {
                "id": o[0],
                "product_id": o[2],
                "quantity": o[3],
                "created_at": o[4],
            }
            for o in orders
        ],
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": get_timestamp()}


@app.post("/debug/stats")
async def debug_stats():
    """Debug statistics endpoint - utility mixed in."""
    users = get_all_users_from_db()
    return {
        "total_users": len(users),
        "timestamp": get_timestamp(),
        "version": "1.0.0",
    }
