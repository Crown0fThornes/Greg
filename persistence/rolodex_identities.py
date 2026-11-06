"""Provisional historical people: normalized grouping, explicit Council resolution."""
from difflib import SequenceMatcher
import json
import re
import unicodedata
import uuid

import emoji
from persistence.neighbor_db import connect


def stripped_name(value):
    # Match clean_nick's intent without importing the bot/command registry.
    value=re.sub(r'<@!?\d+>','',value)
    value=re.sub(r'<a?:\w+:\d+>','',value)
    value=re.sub(r'\[[^\]]*\]|\{[^}]*\}','',value)
    value=emoji.replace_emoji(value,replace='')
    value=unicodedata.normalize('NFKC',value).casefold()
    return ' '.join(''.join(ch if ch.isalnum() or ch.isspace() else ' ' for ch in value).split())


def ensure_event_identity(db,message_id,line,event,subject,guild_id,candidates=()):
    name=stripped_name(subject)
    previous=db.execute('SELECT h.automatic,i.normalized_name FROM historical_identity_event h JOIN historical_identity i ON i.id=h.identity_id WHERE h.message_id=? AND h.line_number=? AND h.event_number=?',
                        (message_id,line,event)).fetchone()
    if previous and (not previous['automatic'] or previous['normalized_name']==name):
        return
    # Empty and very short nicknames are not safe enough to collapse en masse.
    key='name:'+name if len(name.replace(' ',''))>=3 else f'unknown:{message_id}:{line}'
    db.execute('INSERT OR IGNORE INTO historical_identity(guild_id,group_key,normalized_name,label) VALUES (?,?,?,?)',
               (guild_id,key,name,subject))
    identity=db.execute('SELECT id FROM historical_identity WHERE guild_id=? AND group_key=?',(guild_id,key)).fetchone()[0]
    # A new report with a conflicting known-account suggestion must not inherit a
    # prior group's confirmed identity merely because the name was reused.
    root_id=identity
    seen=set()
    while root_id not in seen:
        seen.add(root_id)
        merged=db.execute('SELECT target_id FROM historical_identity_merge WHERE source_id=? ORDER BY id DESC LIMIT 1',(root_id,)).fetchone()
        if merged is None:
            break
        root_id=merged[0]
    revision=db.execute('SELECT user_id FROM historical_identity_revision WHERE identity_id=? ORDER BY id DESC LIMIT 1',(root_id,)).fetchone()
    if revision and revision['user_id'] and candidates:
        from .rolodex_people import linked_accounts
        if set(candidates)-linked_accounts(db,revision['user_id']):
            conflict='conflict:'+name+':'+','.join(map(str,sorted(candidates)))
            db.execute('INSERT OR IGNORE INTO historical_identity(guild_id,group_key,normalized_name,label) VALUES (?,?,?,?)',(guild_id,conflict,name,subject))
            identity=db.execute('SELECT id FROM historical_identity WHERE guild_id=? AND group_key=?',(guild_id,conflict)).fetchone()[0]
    db.execute('INSERT INTO historical_identity_event VALUES (?,?,?,?,1) '
               'ON CONFLICT(message_id,line_number,event_number) DO UPDATE SET identity_id=excluded.identity_id '
               'WHERE historical_identity_event.automatic=1', (message_id,line,event,identity))


def backfill(db):
    for row in db.execute('SELECT e.*,m.guild_id FROM membership_event e JOIN membership_log_message m USING(message_id) '
                          'LEFT JOIN historical_identity_event h USING(message_id,line_number,event_number) '
                          'WHERE e.user_id IS NULL AND h.identity_id IS NULL').fetchall():
        ensure_event_identity(db,row['message_id'],row['line_number'],row['event_number'],row['subject'],row['guild_id'],json.loads(row['candidates']))


def identity_state(db):
    merges={r['source_id']:r['target_id'] for r in db.execute('SELECT * FROM historical_identity_merge ORDER BY id')}
    def root(key):
        seen=set()
        while key in merges:
            if key in seen:
                raise ValueError('Historical identity cycle detected')
            seen.add(key)
            key=merges[key]
        return key
    revisions={}
    for row in db.execute('SELECT * FROM historical_identity_revision ORDER BY id'):
        revisions[row['identity_id']]=dict(row)
    assignments={}
    for row in db.execute('SELECT * FROM historical_identity_event'):
        assignments[(row['message_id'],row['line_number'],row['event_number'])]=root(row['identity_id'])
    return root,revisions,assignments


def groups(db,event_rows):
    root,revisions,_=identity_state(db)
    result={}
    for row in db.execute('SELECT * FROM historical_identity ORDER BY id'):
        key=root(row['id'])
        if key not in result:
            primary=dict(db.execute('SELECT * FROM historical_identity WHERE id=?',(key,)).fetchone())
            revision=revisions.get(key)
            primary.update(confirmed=bool(revision and revision['confirmed']),user_id=revision['user_id'] if revision else None,
                           events=[],variants=set(),candidates=set())
            result[key]=primary
    # Only effective unresolved/or-group-resolved reports belong in these groups.
    for row in event_rows:
        key=row.get('identity_id')
        if key in result and not row['excluded']:
            result[key]['events'].append(row)
            result[key]['variants'].add(row['subject'])
            result[key]['candidates'].update(json.loads(row['candidates']))
    names={}
    for row in db.execute('SELECT user_id,value FROM name_history WHERE value IS NOT NULL'):
        names.setdefault(stripped_name(row['value']),set()).add(row['user_id'])
    # Mentions/direct confirmations provide suggestions, never automatic group attribution.
    for row in db.execute('SELECT subject,user_id FROM membership_event WHERE user_id IS NOT NULL'):
        names.setdefault(stripped_name(row['subject']),set()).add(row['user_id'])
    for item in result.values():
        item['candidates'].update(names.get(item['normalized_name'],()))
        item['variants']=sorted(item['variants'])
        item['candidates']=sorted(item['candidates'])
        item['events'].sort(key=lambda r:(r['occurred_at'],r['message_id'],r['line_number'],r['event_number']))
    return [item for item in result.values() if item['events']]


def similar_groups(group,others):
    matches=[]
    a=group['normalized_name'].replace(' ','')
    if len(a)<4:
        return []
    for other in others:
        b=other['normalized_name'].replace(' ','')
        if other['id']==group['id'] or len(b)<4:
            continue
        score=SequenceMatcher(None,a,b).ratio()
        if score>=0.85:
            matches.append((score,other))
    return sorted(matches,key=lambda pair:(-pair[0],pair[1]['id']))[:5]


def change_identity(store,action,key,value,actor_id,reason):
    from persistence.rolodex import timestamp
    if not reason.strip() or len(reason)>1000:
        raise ValueError('Include a reason (1–1000 characters).')
    with connect(store.path) as db:
        db.execute('BEGIN IMMEDIATE')
        root,revisions,assignments=identity_state(db)
        if action=='split':
            try:
                source_key=tuple(map(int,key.split(':')))
            except ValueError:
                raise ValueError('Use the event key MESSAGE:LINE:EVENT.')
            source=assignments.get(source_key)
            if source is None:
                raise ValueError('No provisional identity for this event.')
            row=db.execute('SELECT * FROM historical_identity WHERE id=?',(source,)).fetchone()
            target=db.execute('INSERT INTO historical_identity(guild_id,group_key,normalized_name,label) VALUES (?,?,?,?)',
                              (row['guild_id'],'split:'+uuid.uuid4().hex,row['normalized_name'],row['label'])).lastrowid
            db.execute('UPDATE historical_identity_event SET identity_id=?,automatic=0 WHERE message_id=? AND line_number=? AND event_number=?',
                       (target,*source_key))
            db.execute('INSERT INTO historical_identity_split(message_id,line_number,event_number,source_id,target_id,actor_id,reason,recorded_at) VALUES (?,?,?,?,?,?,?,?)',
                       (*source_key,source,target,actor_id,reason,timestamp()))
            return target
        key=int(key)
        row=db.execute('SELECT * FROM historical_identity WHERE id=?',(key,)).fetchone()
        if row is None:
            raise ValueError('Unknown historical identity ID.')
        key=root(key)
        if action=='merge':
            target=root(int(value))
            if db.execute('SELECT id FROM historical_identity WHERE id=?',(target,)).fetchone() is None or target==key:
                raise ValueError('Choose a different existing identity.')
            a=revisions.get(key)
            b=revisions.get(target)
            if a and b and a['user_id'] and b['user_id'] and a['user_id']!=b['user_id']:
                raise ValueError('These groups have different confirmed IDs. Use account linking for an account switch, or correct the identity first.')
            # Prefer the confirmed side if only one is confirmed.
            if (bool(a and a['user_id']),bool(a and a['confirmed'])) > (bool(b and b['user_id']),bool(b and b['confirmed'])):
                key,target=target,key
            db.execute('INSERT INTO historical_identity_merge(source_id,target_id,actor_id,reason,recorded_at) VALUES (?,?,?,?,?)',
                       (key,target,actor_id,reason,timestamp()))
            return target
        if action not in ('link','unknown','reopen'):
            raise ValueError('Use identity link, unknown, merge, split, or reopen.')
        user_id=int(value) if action=='link' else None
        if user_id is not None:
            if user_id<=0:
                raise ValueError('Discord ID must be positive.')
            db.execute('INSERT OR IGNORE INTO person(user_id) VALUES (?)',(user_id,))
        db.execute('INSERT INTO historical_identity_revision(identity_id,user_id,confirmed,actor_id,reason,recorded_at) VALUES (?,?,?,?,?,?)',
                   (key,user_id,int(action!='reopen'),actor_id,reason,timestamp()))
        return key


def richer_suggestions(db,group,all_groups):
    """Explain account candidates; evidence is not an automatic identity decision."""
    evidence={}
    def add(uid,reason,strength,url=None):
        if uid is None:
            return
        item=evidence.setdefault(uid,dict(user_id=uid,reasons=[],sources=[],strength=0,conflicts=[]))
        if reason not in item['reasons']:
            item['reasons'].append(reason)
        if url and url not in item['sources']:
            item['sources'].append(url)
        item['strength']=max(item['strength'],strength)
    target=group['normalized_name']
    compact=target.replace(' ','')
    for row in db.execute('SELECT user_id,value,kind,observed_at FROM name_history WHERE value IS NOT NULL'):
        known=stripped_name(row['value'])
        if known and known==target:
            add(row['user_id'],f"Exact cleaned match to recorded {row['kind']} '{row['value']}' (observed {row['observed_at'][:10]})",3)
    for row in db.execute('SELECT e.*,m.channel_id,m.guild_id FROM membership_event e JOIN membership_log_message m USING(message_id) WHERE e.user_id IS NOT NULL'):
        if stripped_name(row['subject'])==target:
            basis='Discord mention' if row['resolution']=='mention' else 'explicit per-message identity'
            url=f"https://discord.com/channels/{row['guild_id']}/{row['channel_id']}/{row['message_id']}"
            add(row['user_id'],f"{basis} connects '{row['subject']}' to this account",4,url)
    target_nhs={r['label'] for r in group['events'] if r['kind']=='neighborhood'}
    for other in all_groups:
        if other['id']==group['id'] or not other['confirmed'] or other['user_id'] is None:
            continue
        other_names={other['normalized_name'],*(stripped_name(v) for v in other['variants'])}
        exact=target in other_names
        similarity=max((SequenceMatcher(None,compact,name.replace(' ','')).ratio() for name in other_names),default=0)
        if not exact and (len(compact)<4 or similarity<0.85):
            continue
        uid=other['user_id']
        event=other['events'][0]
        url=f"https://discord.com/channels/{event['guild_id']}/{event['channel_id']}/{event['message_id']}"
        add(uid, f"Council-confirmed identity #{other['id']} uses the same cleaned name" if exact else
                 f"Similar name to Council-confirmed identity #{other['id']} ({similarity:.0%} spelling similarity, not identity confidence)",4 if exact else 1,url)
        overlap=sorted(target_nhs & {r['label'] for r in other['events'] if r['kind']=='neighborhood'})
        if overlap:
            add(uid,'Supporting context: shared neighborhood reports in '+', '.join(overlap),0)
        start,end=group['events'][0]['occurred_at'][:10],group['events'][-1]['occurred_at'][:10]
        a,b=other['events'][0]['occurred_at'][:10],other['events'][-1]['occurred_at'][:10]
        if start<=b and a<=end:
            add(uid,'Supporting context: report date ranges overlap (not proof of identity)',0)
    for uid in group['candidates']:
        add(uid,'Suggested by an exact cleaned-name match during import; verify the account',2)
    # Resolve account-switch equivalence when flagging conflicting candidates.
    from .rolodex_people import linked_accounts
    for uid,item in evidence.items():
        conflicting=set(evidence)-linked_accounts(db,uid)
        if conflicting:
            item['conflicts'].append('Other account candidates: '+', '.join(map(str,sorted(conflicting))))
        if group['user_id'] and uid not in linked_accounts(db,group['user_id']):
            item['conflicts'].append('Different from this group’s currently confirmed account')
        item['label']='Recorded identity evidence' if item['strength']>=3 else 'Name-based suggestion only'
    return sorted(evidence.values(),key=lambda item:(-item['strength'],item['user_id']))[:5]
