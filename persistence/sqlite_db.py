"""Transaction helper for Rolodex; independent of Neighbor text storage."""
from contextlib import contextmanager
import sqlite3


@contextmanager
def connect(db_path):
    connection=sqlite3.connect(db_path,timeout=30)
    try:
        connection.row_factory=sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        with connection:
            yield connection
    finally:
        connection.close()
