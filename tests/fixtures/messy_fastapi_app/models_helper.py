"""User and Product models - imports database.py (circular dependency)."""

from database import get_db_connection, init_database


class User:
    """User model."""
    
    def __init__(self, id, email, name):
        """Initialize user."""
        self.id = id
        self.email = email
        self.name = name
    
    @staticmethod
    def from_db_row(row):
        """Create User from database row."""
        return User(row[0], row[1], row[2])
    
    def save_to_db(self):
        """Save user to database."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (email, name) VALUES (?, ?)",
            (self.email, self.name)
        )
        conn.commit()
        conn.close()
    
    @staticmethod
    def initialize():
        """Initialize models."""
        init_database()


class Product:
    """Product model."""
    
    def __init__(self, id, name, price, stock):
        """Initialize product."""
        self.id = id
        self.name = name
        self.price = price
        self.stock = stock
    
    @staticmethod
    def from_db_row(row):
        """Create Product from database row."""
        return Product(row[0], row[1], row[2], row[3])
    
    def save_to_db(self):
        """Save product to database."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO products (name, price, stock) VALUES (?, ?, ?)",
            (self.name, self.price, self.stock)
        )
        conn.commit()
        conn.close()
