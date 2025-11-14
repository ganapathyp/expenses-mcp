"""Database connection and initialization for the Expenses API."""
import logging
from pathlib import Path
from typing import Optional
import sqlite3

logger = logging.getLogger(__name__)

# Database configuration
DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "expenses.db"


def get_connection() -> sqlite3.Connection:
    """
    Get a database connection with row factory enabled.
    
    Returns:
        sqlite3.Connection: A connection to the SQLite database.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """
    Initialize the database by creating the expenses table if it doesn't exist.
    
    This function is idempotent and safe to call multiple times.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            """
        )
        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {DB_PATH}")
    except sqlite3.Error as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
