import sqlite3
import hashlib
from datetime import datetime

DATABASE = 'blackbear.db'

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # This allows us to access columns by name
    return conn

def init_db():
    """Initialize database with tables"""
    conn = get_db()
    
    # Users table (intentionally vulnerable)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,  -- Will store plain text (VULNERABILITY)
            display_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_online INTEGER DEFAULT 0
        )
    ''')
    
    # Messages table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER,  -- NULL for group messages
            group_id INTEGER,     -- NULL for direct messages
            content TEXT NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_id) REFERENCES users (id)
        )
    ''')
    
    # Groups table (for Week 4)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_by INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

def create_user(username, email, password, display_name):
    """Create a new user (VULNERABLE - stores plain text password)"""
    conn = get_db()
    try:
        # VULNERABILITY: SQL injection possible, plain text password
        query = f"INSERT INTO users (username, email, password, display_name) VALUES ('{username}', '{email}', '{password}', '{display_name}')"
        conn.execute(query)
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error creating user: {e}")
        return False
    finally:
        conn.close()

def authenticate_user(username, password):
    """Authenticate user (VULNERABLE)"""
    conn = get_db()
    # VULNERABILITY: SQL injection in authentication
    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
    try:
        user = conn.execute(query).fetchone()
        conn.close()
        return dict(user) if user else None
    except sqlite3.Error as e:
        print(f"Authentication error: {e}")
        conn.close()
        return None

def get_user_by_id(user_id):
    """Get user by ID"""
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else None

if __name__ == '__main__':
    init_db()

    