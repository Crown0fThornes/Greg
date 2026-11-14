"""Election settings, receipt references, and aggregate results; no local ballots."""
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3

PATH = Path(__file__).resolve().parent.parent/'data/council_elections.sqlite3'


class ElectionStore:
    def __init__(self,path=PATH):
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS election ('
                       'id INTEGER PRIMARY KEY, config TEXT NOT NULL, status TEXT NOT NULL, '
                       'cutoff REAL, result TEXT, delivery TEXT NOT NULL DEFAULT \'waiting\', message_id INTEGER)')
            db.execute('CREATE TABLE IF NOT EXISTS voter ('
                       'election_id INTEGER NOT NULL,user_id INTEGER NOT NULL,dm_id INTEGER NOT NULL,'
                       'receipt_id INTEGER NOT NULL,submitted REAL NOT NULL,PRIMARY KEY(election_id,user_id))')
            db.execute('CREATE TABLE IF NOT EXISTS invitation ('
                       'election_id INTEGER NOT NULL,user_id INTEGER NOT NULL,last_attempt REAL NOT NULL,'
                       'status TEXT NOT NULL,PRIMARY KEY(election_id,user_id))')
            db.execute('CREATE TABLE IF NOT EXISTS ballot_menu ('
                       'message_id INTEGER PRIMARY KEY,election_id INTEGER NOT NULL,'
                       'user_id INTEGER NOT NULL,dm_id INTEGER NOT NULL,kind TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS menu_repair ('
                       'election_id INTEGER NOT NULL,user_id INTEGER NOT NULL,PRIMARY KEY(election_id,user_id))')
            db.execute('CREATE TABLE IF NOT EXISTS elimination_decision ('
                       'election_id INTEGER NOT NULL,round INTEGER NOT NULL,candidate_id INTEGER NOT NULL,'
                       'actor_id INTEGER NOT NULL,recorded REAL NOT NULL,PRIMARY KEY(election_id,round))')

    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=10)
        db.row_factory=sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def create(self,config):
        with self.connect() as db:
            return db.execute("INSERT INTO election(config,status) VALUES (?,'open')",(json.dumps(config),)).lastrowid

    def get(self,key):
        with self.connect() as db:
            row=db.execute('SELECT * FROM election WHERE id=?',(key,)).fetchone()
        if row is None:
            raise ValueError('Election not found. Use `$election list`.')
        item=dict(row)
        item['config']=json.loads(item['config'])
        item['result']=json.loads(item['result']) if item['result'] else None
        return item

    def all(self,limit=20):
        with self.connect() as db:
            query='SELECT id FROM election ORDER BY id DESC'
            ids=[row[0] for row in db.execute(query if limit is None else query+' LIMIT ?',() if limit is None else (limit,))]
        return [self.get(key) for key in ids]

    def receipts(self,key):
        with self.connect() as db:
            return [dict(row) for row in db.execute('SELECT * FROM voter WHERE election_id=? ORDER BY user_id',(key,))]

    def submit(self,key,user_id,dm_id,receipt_id,when):
        with self.connect() as db:
            db.execute('INSERT INTO voter VALUES (?,?,?,?,?) ON CONFLICT(election_id,user_id) DO UPDATE SET '
                       'dm_id=excluded.dm_id,receipt_id=excluded.receipt_id,submitted=excluded.submitted',
                       (key,user_id,dm_id,receipt_id,when))

    def freeze(self,key,now):
        row=self.get(key)
        with self.connect() as db:
            db.execute("UPDATE election SET status='counting',cutoff=? WHERE id=? AND status='open'",
                       (min(now,row['config']['deadline']),key))
        return self.get(key)

    def finish(self,key,result):
        with self.connect() as db:
            db.execute("UPDATE election SET status='closed',result=? WHERE id=? AND status='counting'",(json.dumps(result),key))

    def cancel(self,key):
        with self.connect() as db:
            db.execute("UPDATE election SET status='cancelled' WHERE id=? AND status='open'",(key,))

    def claim_delivery(self,key):
        with self.connect() as db:
            return bool(db.execute("UPDATE election SET delivery='pending' WHERE id=? AND status='closed' AND delivery='waiting'",(key,)).rowcount)

    def delivery(self,key,status,message_id=None):
        with self.connect() as db:
            db.execute('UPDATE election SET delivery=?,message_id=? WHERE id=?',(status,message_id,key))

    def invitations(self,key):
        with self.connect() as db:
            return {row['user_id']:dict(row) for row in db.execute('SELECT * FROM invitation WHERE election_id=?',(key,))}

    def claim_invitation(self,key,uid,now):
        with self.connect() as db:
            return bool(db.execute("INSERT INTO invitation VALUES (?,?,?,'pending') "
                "ON CONFLICT(election_id,user_id) DO UPDATE SET last_attempt=excluded.last_attempt,status='pending' "
                'WHERE invitation.last_attempt<=?',(key,uid,now,now-86400)).rowcount)

    def invitation_status(self,key,uid,status):
        with self.connect() as db:
            db.execute('UPDATE invitation SET status=? WHERE election_id=? AND user_id=?',(status,key,uid))

    def menus(self,key):
        with self.connect() as db:
            return [dict(row) for row in db.execute('SELECT * FROM ballot_menu WHERE election_id=?',(key,))]

    def menu(self,key,uid,dm_id,message_id,kind):
        with self.connect() as db:
            db.execute('INSERT INTO ballot_menu VALUES (?,?,?,?,?) ON CONFLICT(message_id) DO UPDATE SET kind=excluded.kind',
                       (message_id,key,uid,dm_id,kind))

    def forget_menu(self,message_id):
        with self.connect() as db:
            db.execute('DELETE FROM ballot_menu WHERE message_id=?',(message_id,))

    def repaired(self,key,uid):
        with self.connect() as db:
            return bool(db.execute('SELECT 1 FROM menu_repair WHERE election_id=? AND user_id=?',(key,uid)).fetchone())

    def mark_repaired(self,key,uid):
        with self.connect() as db:
            db.execute('INSERT OR IGNORE INTO menu_repair VALUES (?,?)',(key,uid))

    def decisions(self,key):
        with self.connect() as db:
            return [dict(row) for row in db.execute('SELECT * FROM elimination_decision WHERE election_id=? ORDER BY round',(key,))]

    def recount(self,key,result,decision=None):
        with self.connect() as db:
            if decision is not None:
                db.execute('INSERT INTO elimination_decision VALUES (?,?,?,?,?)',
                           (key,decision['round'],decision['candidate_id'],decision['actor_id'],decision['recorded']))
            db.execute("UPDATE election SET result=?,delivery='waiting' WHERE id=? AND status='closed'",
                       (json.dumps(result),key))
