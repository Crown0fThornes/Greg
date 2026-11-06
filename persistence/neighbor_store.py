"""SQLite records plus recoverable, atomic replacements of legacy text shards."""

from contextlib import contextmanager
import os
from pathlib import Path
import stat
import tempfile
import threading

from . import neighbor_db

_storage_lock = threading.RLock()
_stores = {}


def _atomic_replace(path, contents):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as output:
            temporary = Path(output.name)
            output.write(contents)
            output.flush()
            os.fsync(output.fileno())
        temporary.chmod(mode)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


class Session:
    def __init__(self, db):
        self.db = db
        self.original_files = {}

    def mirror(self, path, contents):
        path = Path(path)
        if path not in self.original_files:
            self.original_files[path] = path.read_bytes() if path.exists() else None
        if path.exists() and path.read_bytes() == contents:
            return
        _atomic_replace(path, contents)

    def restore_text(self):
        errors = []
        for path, original in reversed(list(self.original_files.items())):
            try:
                if original is None:
                    path.unlink(missing_ok=True)
                elif not path.exists() or path.read_bytes() != original:
                    _atomic_replace(path, original)
            except BaseException as error:
                errors.append(error)
        return errors

    def keys(self):
        if self.db is None:
            return set()
        return {tuple(row) for row in self.db.execute("SELECT user_id, guild_id FROM neighbor")}

    def load(self, user_id, guild_id):
        if self.db is None:
            return None
        row = self.db.execute("SELECT * FROM neighbor WHERE user_id = ? AND guild_id = ?",
                              (user_id, guild_id)).fetchone()
        if row is None:
            return None
        items = []
        for item in self.db.execute(
                "SELECT * FROM item WHERE user_id = ? AND guild_id = ? ORDER BY inventory_position",
                (user_id, guild_id)):
            attributes = dict(self.db.execute("SELECT name, value FROM item_attribute WHERE item_id = ?",
                                               (item["item_id"],)).fetchall())
            items.append(dict(item_id=item["item_id"], name=item["name"], type=item["type"],
                              expiration=item["expiration"], values=attributes))
        return dict(user_id=user_id, guild_id=guild_id, xp=row["xp"], legacy_xp=row["legacy_xp"], items=items)

    def save(self, record):
        if self.db is None:
            return []
        uid, gid = record["user_id"], record["guild_id"]
        self.db.execute(
            "INSERT INTO neighbor (user_id, guild_id, xp, legacy_xp) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(user_id, guild_id) DO UPDATE SET xp = excluded.xp, legacy_xp = excluded.legacy_xp",
            (uid, gid, record["xp"], record["legacy_xp"]))
        existing = self.db.execute("SELECT item_id, inventory_position FROM item WHERE user_id = ? AND guild_id = ?",
                                    (uid, gid)).fetchall()
        existing_ids = {row["item_id"] for row in existing}
        # Move positions out of the way before reordering, retaining item IDs.
        offset = max((row["inventory_position"] for row in existing), default=-1) + len(record["items"]) + 1
        self.db.execute("UPDATE item SET inventory_position = inventory_position + ? WHERE user_id = ? AND guild_id = ?",
                        (offset, uid, gid))
        retained = []
        for position, item in enumerate(record["items"]):
            item_id = item.get("item_id")
            if item_id in existing_ids and item_id not in retained:
                self.db.execute("UPDATE item SET name = ?, type = ?, expiration = ?, inventory_position = ? WHERE item_id = ?",
                                (item["name"], item["type"], item["expiration"], position, item_id))
                self.db.execute("DELETE FROM item_attribute WHERE item_id = ?", (item_id,))
            else:
                item_id = self.db.execute(
                    "INSERT INTO item (user_id, guild_id, name, type, expiration, inventory_position) VALUES (?, ?, ?, ?, ?, ?)",
                    (uid, gid, item["name"], item["type"], item["expiration"], position)).lastrowid
            retained.append(item_id)
            self.db.executemany("INSERT INTO item_attribute (item_id, name, value) VALUES (?, ?, ?)",
                                [(item_id, str(key), str(value)) for key, value in item["values"].items()])
        for item_id in existing_ids - set(retained):
            self.db.execute("DELETE FROM item WHERE item_id = ?", (item_id,))
        return retained

    def delete(self, user_id, guild_id):
        if self.db is not None:
            self.db.execute("DELETE FROM neighbor WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))


class NeighborStore:
    def __init__(self, db_path, source="sqlite"):
        self.db_path = Path(db_path)
        self.source = source
        self._initialized = False
        self._local = threading.local()

    @contextmanager
    def transaction(self):
        with _storage_lock:
            active = getattr(self._local, "session", None)
            if active is not None:
                yield active
                return
            if self.source == "sqlite" and not self._initialized:
                neighbor_db.initialize_database(self.db_path)
                self._initialized = True
            # connect() commits on success and rolls back on exceptions. Keep
            # the text undo state alive until that commit has also succeeded.
            session = Session(None)
            try:
                if self.source == "sqlite":
                    with neighbor_db.connect(self.db_path) as db:
                        db.execute("BEGIN IMMEDIATE")
                        session.db = db
                        self._local.session = session
                        yield session
                else:
                    self._local.session = session
                    yield session
            except BaseException as error:
                errors = session.restore_text()
                if errors:
                    raise BaseExceptionGroup("Neighbor write failed and some text backups could not be restored",
                                             [error, *errors]) from error
                raise
            finally:
                self._local.session = None


def get_store():
    source = os.environ.get("GREG_NEIGHBOR_STORAGE", "sqlite").lower()
    if source not in {"sqlite", "text"}:
        raise ValueError("GREG_NEIGHBOR_STORAGE must be 'sqlite' or 'text'")
    path = Path(os.environ.get("GREG_NEIGHBOR_DB", str(neighbor_db.DEFAULT_DB_PATH))).resolve()
    key = (str(path), source)
    with _storage_lock:
        if key not in _stores:
            _stores[key] = NeighborStore(path, source)
        return _stores[key]
