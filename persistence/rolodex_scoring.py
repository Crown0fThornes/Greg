"""First-clearance points for Council review, independent of player XP."""
from persistence.rolodex import timestamp


def queued_records(db):
    from .rolodex_identities import identity_state
    from .rolodex_records import records
    _,revisions,_=identity_state(db)
    return {(r['message_id'],r['line_number'],r['event_number']) for r in records(db)['event']
            if r['user_id'] is None and not r['excluded']
            and not revisions.get(r.get('identity_id'),{}).get('confirmed',False)}


def award_cleared(db,before,actor_id,action):
    cleared=before-queued_records(db)
    now=timestamp()
    for key in sorted(cleared):
        db.execute('INSERT OR IGNORE INTO rolodex_review_point VALUES (?,?,?,?,?,?)',
                   (*key,actor_id,action,now))
    return len(cleared)


def leaderboard(db):
    return [dict(row) for row in db.execute('SELECT actor_id,COUNT(*) AS points FROM rolodex_review_point '
                                          'GROUP BY actor_id ORDER BY points DESC,actor_id')]
