"""Reversible account associations and versioned Council notes; no XP transfers."""
from persistence.neighbor_db import connect
from persistence.rolodex import timestamp


def check_reason(reason):
    if not reason.strip() or len(reason) > 1000:
        raise ValueError('Include a reason (1–1000 characters).')


def account_groups(db):
    latest = {}
    for row in db.execute('SELECT * FROM rolodex_account_link ORDER BY id'):
        latest[(row['old_user_id'], row['new_user_id'])] = dict(row)
    return [row for row in latest.values() if row['active']]


def linked_accounts(db, user_id):
    edges = account_groups(db)
    found = {user_id}
    changed = True
    while changed:
        changed = False
        for row in edges:
            pair = {row['old_user_id'], row['new_user_id']}
            if found & pair and not pair <= found:
                found |= pair
                changed = True
    return found


def link_accounts(store, old, new, actor_id, actor_name, reason, *, active=True):
    check_reason(reason)
    if old <= 0 or new <= 0 or old == new:
        raise ValueError('Choose two different positive Discord IDs.')
    with connect(store.path) as db:
        db.execute('BEGIN IMMEDIATE')
        links = account_groups(db)
        if active:
            if new in linked_accounts(db, old):
                raise ValueError('Those accounts are already connected.')
        elif not any(r['old_user_id'] == old and r['new_user_id'] == new for r in links):
            raise ValueError('No active link in that old/new order. Use $rolodex accounts @user.')
        db.executemany('INSERT OR IGNORE INTO person(user_id) VALUES (?)', [(old,), (new,)])
        return db.execute('INSERT INTO rolodex_account_link '
                          '(old_user_id,new_user_id,active,actor_id,actor_name,reason,recorded_at) '
                          'VALUES (?,?,?,?,?,?,?)',
                          (old,new,int(active),actor_id,actor_name,reason.strip(),timestamp())).lastrowid


def notes(db, accounts):
    latest, original = {}, {}
    for row in db.execute('SELECT * FROM rolodex_note_revision ORDER BY id'):
        original.setdefault(row['note_id'], dict(row))
        latest[row['note_id']] = dict(row)
    result = []
    for key, row in latest.items():
        if row['user_id'] in accounts and not row['deleted']:
            row['added_by'] = original[key]['actor_name']
            row['added_by_id'] = original[key]['actor_id']
            result.append(row)
    return result


def save_note(store, user_id, body, actor_id, actor_name, *, note_id=None, reason='Added Council note', deleted=False):
    check_reason(reason)
    if not deleted and (not body.strip() or len(body) > 1000):
        raise ValueError('Notes must contain 1–1000 characters.')
    with connect(store.path) as db:
        db.execute('BEGIN IMMEDIATE')
        if note_id is None:
            if user_id is None or user_id <= 0 or deleted:
                raise ValueError('Choose a valid Discord ID.')
            note_id = db.execute('SELECT COALESCE(MAX(note_id),0)+1 FROM rolodex_note_revision').fetchone()[0]
            db.execute('INSERT OR IGNORE INTO person(user_id) VALUES (?)', (user_id,))
        else:
            previous = db.execute('SELECT * FROM rolodex_note_revision WHERE note_id=? ORDER BY id DESC LIMIT 1', (note_id,)).fetchone()
            if previous is None:
                raise ValueError('Note not found.')
            user_id = previous['user_id']
            if deleted:
                body = previous['body']
        db.execute('INSERT INTO rolodex_note_revision '
                   '(note_id,user_id,body,deleted,actor_id,actor_name,reason,recorded_at) VALUES (?,?,?,?,?,?,?,?)',
                   (note_id,user_id,body.strip(),int(deleted),actor_id,actor_name,reason.strip(),timestamp()))
        return note_id
