"""Observed identity and membership history, independent of XP/inventory storage."""

from contextlib import nullcontext
from datetime import datetime, timezone
import json
from pathlib import Path

from persistence.neighbor_db import connect

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT / 'data' / 'rolodex.sqlite3'
FF_GUILD = 647883751853916162
NEIGHBORHOODS = {
    1024052938752151552: 'FFP', 656112994392080384: 'FF',
    689928709683150909: 'FFJ', 1334660124639236267: 'FFJ2',
    1173325157767589988: 'FFG', 1342329111359656008: 'FFC',
    1034248720058945577: 'FFR',
}


def timestamp(value=None):
    value = value or datetime.now(timezone.utc)
    if value.tzinfo is None:
        raise ValueError('Rolodex timestamps must include a timezone')
    return value.astimezone(timezone.utc).isoformat()


class Rolodex:
    def __init__(self, db_path=DEFAULT_DB_PATH):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with connect(self.path) as db:
            version = db.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, 1, 2, 3, 4):
                raise ValueError(f'Unsupported Rolodex schema version: {version}')
            db.executescript('BEGIN IMMEDIATE;\n' + Path(__file__).with_name(
                'rolodex_schema.sql').read_text() + '\nPRAGMA user_version=4;\nCOMMIT;')
        config = json.loads((ROOT / 'lookups' / 'rolodex_families.json').read_text())
        self.family_roles = {}
        for family in config['families']:
            for field, honorary in [('role_id', False), ('honorary_role_id', True)]:
                if family.get(field):
                    self.family_roles[family[field]] = (family['name'], config['season'], honorary)

    @staticmethod
    def _name(db, user_id, guild_id, kind, value, now, source):
        last = db.execute(
            'SELECT value FROM name_history WHERE user_id=? AND guild_id=? AND kind=? '
            'ORDER BY id DESC LIMIT 1', (user_id, guild_id, kind)).fetchone()
        if last is None or last['value'] != value:
            db.execute('INSERT INTO name_history '
                       '(user_id,guild_id,kind,value,observed_at,source) VALUES (?,?,?,?,?,?)',
                       (user_id, guild_id, kind, value, now, source))

    def _identity(self, db, user, now, source):
        db.execute('INSERT OR IGNORE INTO person(user_id) VALUES (?)', (user.id,))
        self._name(db, user.id, 0, 'username', user.name, now, source)
        self._name(db, user.id, 0, 'global_name', user.global_name, now, source)

    def observe_user(self, user, *, at=None, source='observation', _db=None):
        with (nullcontext(_db) if _db is not None else connect(self.path)) as db:
            self._identity(db, user, timestamp(at), source)

    def user_updated(self, before, after, *, at=None):
        # Preserve the old value even if this is the first time we see this user.
        at = at or datetime.now(timezone.utc)
        with connect(self.path) as db:
            self.observe_user(before, at=at, _db=db)
            self.observe_user(after, at=at, source='gateway', _db=db)

    def _roles(self, member):
        result = {}
        if member.guild.id != FF_GUILD:
            return result
        for role in member.roles:
            if role.id in NEIGHBORHOODS:
                result[('neighborhood', str(role.id))] = (
                    NEIGHBORHOODS[role.id], None, False, role.id)
            if role.id in self.family_roles:
                name, season, honorary = self.family_roles[role.id]
                result[('family', f'{season}:{role.id}')] = (name, season, honorary, role.id)
        return result

    def observe_member(self, member, *, at=None, source='observation', left=False, _db=None):
        if member.bot:
            return
        now = timestamp(at)
        desired = {} if left else self._roles(member)
        if not left:
            desired[('server', 'server')] = (member.guild.name, None, False, None)
        with (nullcontext(_db) if _db is not None else connect(self.path)) as db:
            self._identity(db, member, now, source)
            self._name(db, member.id, member.guild.id, 'nickname', member.nick, now, source)
            current = {(r['kind'], r['membership_key']): r for r in db.execute(
                'SELECT * FROM membership WHERE user_id=? AND guild_id=? '
                'AND end_observed_at IS NULL', (member.id, member.guild.id))}
            # Discord's joined_at identifies a new server stay, even across downtime.
            joined_at = timestamp(member.joined_at) if member.joined_at else None
            server = current.get(('server', 'server'))
            new_stay = server and joined_at and server['started_at'] and server['started_at'] != joined_at
            for key, row in current.items():
                if key not in desired or new_stay:
                    db.execute('UPDATE membership SET ended_at=?,end_observed_at=?,end_source=? '
                               'WHERE id=?',
                               (now if source == 'gateway' else None, now, source, row['id']))
            for (kind, key), (label, season, honorary, role_id) in desired.items():
                if (kind, key) in current and not new_stay:
                    continue
                start = joined_at if kind == 'server' else (now if source == 'gateway' else None)
                start_source = 'discord_joined_at' if kind == 'server' and joined_at else source
                db.execute('INSERT INTO membership '
                           '(user_id,guild_id,kind,membership_key,label,season,honorary,role_id,'
                           'started_at,first_observed_at,start_source) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                           (member.id, member.guild.id, kind, key, label, season, honorary,
                            role_id, start, now, start_source))

    def member_updated(self, before, after, *, at=None):
        at = at or datetime.now(timezone.utc)
        with connect(self.path) as db:
            self.observe_member(before, at=at, _db=db)
            self.observe_member(after, at=at, source='gateway', _db=db)

    def member_left(self, member, *, at=None):
        at = at or datetime.now(timezone.utc)
        with connect(self.path) as db:
            latest = db.execute(
                "SELECT * FROM membership WHERE user_id=? AND guild_id=? AND kind='server' "
                'ORDER BY id DESC LIMIT 1', (member.id, member.guild.id)).fetchone()
            joined = timestamp(member.joined_at) if member.joined_at else None
            if latest and latest['end_observed_at'] and latest['started_at'] == joined:
                return
            self.observe_member(member, at=at, _db=db)
            self.observe_member(member, at=at, source='gateway', left=True, _db=db)

    def history(self, user_id):
        """Return plain records for a future command; does not mention/ping anyone."""
        with connect(self.path) as db:
            return {table: [dict(row) for row in db.execute(
                f'SELECT * FROM {table} WHERE user_id=? ORDER BY id', (user_id,))]
                    for table in ('name_history', 'membership', 'membership_event')}
