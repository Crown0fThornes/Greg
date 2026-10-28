"""Council corrections overlay original evidence and remain append-only/auditable."""
from datetime import datetime
import json

from persistence.neighbor_db import connect
from persistence.rolodex import FF_GUILD, NEIGHBORHOODS, timestamp

TABLES = {'membership': 'membership', 'name': 'name_history',
          'event': 'membership_event', 'manual': 'rolodex_manual_event'}
FIELDS = {
    'membership': {'user_id', 'label', 'season', 'honorary', 'started_at', 'ended_at', 'excluded'},
    'name': {'user_id', 'value', 'excluded'},
    'event': {'user_id', 'label', 'action', 'occurred_at', 'excluded'},
    'manual': {'user_id', 'label', 'action', 'occurred_at', 'excluded'},
}


def record_key(kind, row):
    if kind == 'event':
        return f"{row['message_id']}:{row['line_number']}:{row['event_number']}"
    return str(row['id'])


def records(db):
    edits = {}
    for row in db.execute('SELECT * FROM rolodex_edit ORDER BY id'):
        edits[(row['record_type'], row['record_key'], row['field'])] = row
    result = {}
    for kind, table in TABLES.items():
        rows = []
        query = ('SELECT e.*,m.guild_id,m.channel_id FROM membership_event e '
                 'JOIN membership_log_message m USING(message_id)' if kind == 'event'
                 else f'SELECT * FROM {table}')
        for saved in db.execute(query):
            row = dict(saved)
            if row['guild_id'] not in (0, FF_GUILD):
                continue
            key = record_key(kind, row)
            row.update(record_key=key, record_type=kind, excluded=False, corrected=False)
            for field in FIELDS[kind]:
                edit = edits.get((kind, key, field))
                if edit and edit['operation'] == 'set':
                    row[field] = json.loads(edit['new_value'])
                    row['corrected'] = True
            rows.append(row)
        result[kind] = rows
    return result


def validate(kind, field, value, row):
    if field not in FIELDS.get(kind, set()):
        raise ValueError('That field cannot be edited. Use $rolodex help for editable fields.')
    if field == 'user_id':
        if value is None and kind == 'event':
            return None
        value = int(value)
        if value <= 0:
            raise ValueError('User ID must be positive.')
    elif field in ('excluded', 'honorary'):
        if str(value).lower() not in ('true', 'false', '1', '0'):
            raise ValueError('Use true or false.')
        value = str(value).lower() in ('true', '1')
    elif field == 'season':
        value = None if value is None else int(value)
        if value is not None and not 2000 <= value <= 2200:
            raise ValueError('Use a year between 2000 and 2200.')
    elif field in ('started_at', 'ended_at', 'occurred_at'):
        if value is None:
            if field == 'occurred_at':
                raise ValueError('An event needs a date.')
        else:
            date = datetime.fromisoformat(value)
            if date.tzinfo is None:
                from zoneinfo import ZoneInfo
                date = date.replace(tzinfo=ZoneInfo('America/New_York'))
            value = timestamp(date)
    elif field == 'action' and value not in ('join', 'leave'):
        raise ValueError('Action must be join or leave.')
    elif field == 'label':
        if row.get('kind') == 'neighborhood':
            value = str(value).upper()
            if value == 'FFM':
                value = 'FF'
            if value not in NEIGHBORHOODS.values():
                raise ValueError('Unknown neighborhood.')
        if not value or len(value) > 100:
            raise ValueError('Label must be 1–100 characters.')
    elif field == 'value' and value is not None and len(value) > 100:
        raise ValueError('Name is too long.')
    return value


def edit_record(store, kind, key, field, value, actor_id, reason, *, reset=False):
    if not reason.strip() or len(reason) > 1000:
        raise ValueError('Include a reason (1–1000 characters).')
    with connect(store.path) as db:
        db.execute('BEGIN IMMEDIATE')
        row = next((r for r in records(db).get(kind, []) if r['record_key'] == key), None)
        if row is None:
            raise ValueError('Record not found in FF. Use $rolodex review or raw to get its key.')
        if field not in FIELDS[kind]:
            raise ValueError('That field cannot be edited.')
        if not reset:
            value = validate(kind, field, value, row)
            if kind == 'membership' and field in ('started_at', 'ended_at'):
                start = value if field == 'started_at' else row['started_at']
                end = value if field == 'ended_at' else row['ended_at']
                if start and end and start > end:
                    raise ValueError('The end cannot precede the start.')
        cursor = db.execute('INSERT INTO rolodex_edit '
                           '(record_type,record_key,field,operation,old_value,new_value,actor_id,reason,recorded_at) '
                           'VALUES (?,?,?,?,?,?,?,?,?)',
                           (kind, key, field, 'reset' if reset else 'set', json.dumps(row.get(field)),
                            json.dumps(value), actor_id, reason.strip(), timestamp()))
        return cursor.lastrowid


def add_event(store, user_id, action, label, date, actor_id, reason):
    if not reason.strip() or len(reason) > 1000:
        raise ValueError('Include a reason (1–1000 characters).')
    row = {'kind': 'neighborhood'}
    uid = validate('manual', 'user_id', user_id, row)
    label = validate('manual', 'label', label, row)
    action = validate('manual', 'action', action, row)
    date = validate('manual', 'occurred_at', date, row)
    with connect(store.path) as db:
        db.execute('INSERT OR IGNORE INTO person(user_id) VALUES (?)', (uid,))
        return db.execute('INSERT INTO rolodex_manual_event '
                          '(user_id,guild_id,kind,label,action,occurred_at,actor_id,reason,recorded_at) '
                          "VALUES (?,?,'neighborhood',?,?,?,?,?,?)",
                          (uid, FF_GUILD, label, action, date, actor_id, reason.strip(), timestamp())).lastrowid
