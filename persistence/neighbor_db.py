"""SQLite connection/schema setup; no player import happens here."""

from contextlib import contextmanager
from pathlib import Path
import sqlite3

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "neighbors.sqlite3"
SCHEMA_VERSION = 1


@contextmanager
def connect(db_path=DEFAULT_DB_PATH):
    connection = sqlite3.connect(db_path, timeout=30)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_database(db_path=DEFAULT_DB_PATH):
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as db:
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, SCHEMA_VERSION):
            raise ValueError(f"Unsupported Neighbor database schema version: {version}")
        schema = Path(__file__).with_name("neighbor_schema.sql").read_text(encoding="utf-8")
        db.executescript("BEGIN IMMEDIATE;\n" + schema +
                         f"\nPRAGMA user_version = {SCHEMA_VERSION};\nCOMMIT;")
    return path


if __name__ == "__main__":
    print(initialize_database())
