import os
import sqlite3
from flask import g

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "laundry.db")
SCHEMA = os.path.join(BASE_DIR, "schema.sql")


def get_db():
    """Open a new database connection if there isn't one for the current app context."""
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db



def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create tables (and seed data) if they don't exist yet."""
    conn = sqlite3.connect(DATABASE)
    with open(SCHEMA, encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


def init_app(app):
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()