"""Database connection and operations - imports models_helper.py (circular dependency)."""

import sqlite3
from models_helper import User, Product


_db_path = ":memory:"


def get_db_connection():
    """Get database connection."""
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialize database with tables."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)
    
    conn.commit()
    conn.close()


def seed_test_data():
    """Seed database with test data."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create test users
    cursor.execute(
        "INSERT INTO users (email, password, name) VALUES (?, ?, ?)",
        ("test@example.com", "hashedpw123", "Test User")
    )
    cursor.execute(
        "INSERT INTO users (email, password, name) VALUES (?, ?, ?)",
        ("admin@example.com", "hashedpw456", "Admin User")
    )
    
    # Create test products
    cursor.execute(
        "INSERT INTO products (name, price, stock) VALUES (?, ?, ?)",
        ("Widget", 9.99, 100)
    )
    cursor.execute(
        "INSERT INTO products (name, price, stock) VALUES (?, ?, ?)",
        ("Gadget", 19.99, 50)
    )
    
    conn.commit()
    conn.close()


def get_user_model(user_id):
    """Get user as model object."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, name FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return User.from_db_row(row)
    return None


def get_product_model(product_id):
    """Get product as model object."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price, stock FROM products WHERE id = ?", (product_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return Product.from_db_row(row)
    return None


def save_user_model(user):
    """Save user model to database."""
    user.save_to_db()


def save_product_model(product):
    """Save product model to database."""
    product.save_to_db()
