"""Import join/leave channel evidence: python -m persistence.import_membership_history."""

import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
import re
import unicodedata

from persistence.neighbor_db import connect
from persistence.rolodex import DEFAULT_DB_PATH, FF_GUILD, ROOT, Rolodex, timestamp

JOINLIST = 943263445724311572
LEAVELIST = 1138557740185305169
MENTION = re.compile(r'<@!?(\d+)>')
LINE = re.compile(
    r'^(?P<subject>.+?)\s+has\s+(?P<verb>joined|left)\s+'
    r'(?P<nh>ffj2|ffp|ffj|ffg|ffc|ffr|ff)\b'
    r'(?P<server>\s+and\s+(?:the\s+)?server)?[.!\s]*$', re.IGNORECASE)


def normalized(name):
    # Deliberately do not strip family tags/emojis or use fuzzy matching.
    return unicodedata.normalize('NFKC', name).strip().casefold()


class HistoryImporter:
    def __init__(self, store, greg_id, overrides=None):
        self.store = store
        self.greg_id = greg_id
        self.overrides = overrides or {}
        self.names = defaultdict(set)
        with connect(store.path) as db:
            for row in db.execute('SELECT user_id,value FROM name_history WHERE guild_id IN (0,?)',
                                  (FF_GUILD,)):
                if row['value']:
                    self.names[normalized(row['value'])].add(row['user_id'])

    def add_member(self, member):
        for value in (member.name, member.global_name, member.nick, member.display_name):
            if value:
                self.names[normalized(value)].add(member.id)

    def resolve(self, message, line_number, subject):
        override = self.overrides.get(f'{message.id}:{line_number}')
        if override is not None:
            if isinstance(override, bool) or not isinstance(override, int) or override <= 0:
                raise ValueError('Overrides must be positive integer Discord user IDs')
            return override, 'manual', []
        mentions = {int(uid) for uid in MENTION.findall(subject)}
        if len(mentions) == 1:
            return mentions.pop(), 'mention', []
        candidates = sorted(self.names.get(normalized(subject), ()))
        # Even a unique historical/display name is only a suggestion: names can be reused.
        return None, 'unresolved', candidates

    def ingest(self, message):
        if message.guild.id != FF_GUILD or message.channel.id not in (JOINLIST, LEAVELIST):
            raise ValueError('Message is outside the configured FF history channels')
        counts = {'resolved': 0, 'unresolved': 0, 'unparsed_lines': 0}
        with connect(self.store.path) as db:
            db.execute('INSERT INTO membership_log_message VALUES (?,?,?,?,?,?,?) '
                       'ON CONFLICT(message_id) DO UPDATE SET content=excluded.content, '
                       'imported_at=excluded.imported_at',
                       (message.id, message.guild.id, message.channel.id, message.author.id,
                        timestamp(message.created_at), message.content, timestamp()))
            # Reparse edited posts and apply new resolutions without leaving duplicate evidence.
            db.execute('DELETE FROM membership_event WHERE message_id=?', (message.id,))
            for number, line in enumerate(message.content.splitlines(), 1):
                if not line.strip():
                    continue
                match = LINE.fullmatch(line.strip())
                if not match:
                    counts['unparsed_lines'] += 1
                    continue
                subject = match['subject']
                uid, resolution, candidates = self.resolve(message, number, subject)
                if uid is not None:
                    db.execute('INSERT OR IGNORE INTO person(user_id) VALUES (?)', (uid,))
                counts['resolved' if uid is not None else 'unresolved'] += 1
                targets = [('neighborhood', match['nh'].upper())]
                if match['server']:
                    targets.append(('server', 'server'))
                for event_number, (kind, label) in enumerate(targets):
                    db.execute('INSERT INTO membership_event '
                               '(message_id,line_number,event_number,user_id,subject,action,kind,label,'
                               'occurred_at,resolution,candidates) VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                               (message.id, number, event_number, uid, subject,
                                'join' if match['verb'].lower() == 'joined' else 'leave', kind,
                                label, timestamp(message.created_at), resolution, json.dumps(candidates)))
        return counts

    def review(self):
        with connect(self.store.path) as db:
            unresolved = [dict(row) for row in db.execute(
                'SELECT e.*,m.channel_id,m.guild_id,m.content FROM membership_event e '
                'JOIN membership_log_message m USING(message_id) WHERE user_id IS NULL '
                'ORDER BY occurred_at,message_id,line_number')]
            unparsed = []
            for message in db.execute('SELECT * FROM membership_log_message ORDER BY posted_at,message_id'):
                for number, line in enumerate(message['content'].splitlines(), 1):
                    if line.strip() and not LINE.fullmatch(line.strip()):
                        unparsed.append(dict(message_id=message['message_id'],
                                             channel_id=message['channel_id'], line_number=number,
                                             content=line))
            return {'unresolved': unresolved, 'unparsed': unparsed}


def main():
    import discord
    from dotenv import load_dotenv

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument('--overrides', type=Path, help='JSON {"message_id:line_number": user_id}')
    parser.add_argument('--review', type=Path, default=ROOT / 'data' / 'rolodex_import_review.json')
    args = parser.parse_args()
    overrides = json.loads(args.overrides.read_text()) if args.overrides else {}
    load_dotenv(ROOT / '.env')
    token = os.environ['BOT_TOKEN']
    store = Rolodex(args.db)
    intents = discord.Intents.none()
    intents.guilds = True
    intents.members = True
    intents.message_content = True

    class ImportClient(discord.Client):
        async def on_ready(self):
            if getattr(self, 'import_started', False):
                return
            self.import_started = True
            try:
                guild = self.get_guild(FF_GUILD)
                if guild is None:
                    raise RuntimeError('Bot cannot access the FF guild')
                await guild.chunk()
                importer = HistoryImporter(store, self.user.id, overrides)
                for member in guild.members:
                    importer.add_member(member)
                total = dict(messages=0, resolved=0, unresolved=0, unparsed_lines=0)
                for channel_id in (JOINLIST, LEAVELIST):
                    channel = await self.fetch_channel(channel_id)
                    async for message in channel.history(limit=None, oldest_first=True):
                        result = importer.ingest(message)
                        total['messages'] += 1
                        for key, count in result.items():
                            total[key] += count
                        if total['messages'] % 500 == 0:
                            print(f"Read {total['messages']} messages", flush=True)
                args.review.parent.mkdir(parents=True, exist_ok=True)
                args.review.write_text(json.dumps(importer.review(), indent=2, ensure_ascii=False)+'\n')
                print(json.dumps(total))
                print(f'Review report: {args.review}')
            except Exception:
                self.failed = True
                raise
            finally:
                await self.close()

    client = ImportClient(intents=intents)
    client.run(token)
    if getattr(client, 'failed', False):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
