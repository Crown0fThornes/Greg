"""Initialize Neighbor's future SQLite storage without changing live storage.

Run from the project root: python -m persistence.neighbor_db
"""

from contextlib import contextmanager
from pathlib import Path
import sqlite3


DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "neighbors.sqlite3"
SCHEMA_PATH = Path(__file__).with_name("neighbor_schema.sql")
SCHEMA_VERSION = 1


@contextmanager
def connect(db_path=DEFAULT_DB_PATH):
    """Open a transaction with foreign keys enabled; always close its connection.

    Successful blocks commit. Exceptions roll back pending changes. Initialization
    is separate, so importing or connecting never silently migrates a database.
    """
    connection = sqlite3.connect(db_path, timeout=10)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_database(db_path=DEFAULT_DB_PATH):
    """Create the three tables atomically and retain any existing rows."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as connection:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, SCHEMA_VERSION):
            raise ValueError(f"Unsupported Neighbor database schema version: {version}")
        schema = SCHEMA_PATH.read_text(encoding="utf-8")
        connection.executescript(
            "BEGIN IMMEDIATE;\n" + schema
            + f"\nPRAGMA user_version = {SCHEMA_VERSION};\nCOMMIT;"
        )
    return db_path


if __name__ == "__main__":
    print(f"Initialized Neighbor tables in {initialize_database()}")
