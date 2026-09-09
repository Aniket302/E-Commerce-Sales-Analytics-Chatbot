import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "olist.db"

def get_connection():
    connection = sqlite3.connect(DB_PATH)

    # Return rows that behave like dictionaries.
    connection.row_factory = sqlite3.Row

    # Make sure foreign key enforcement is enabled.
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


# Instead of every tool doing:
# sqlite3.connect(...)
# we'll simply do:
# connection = get_connection()