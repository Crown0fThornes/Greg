"""Privileged Rolodex lookup and Council reconciliation commands."""
from datetime import datetime
import json
import re
from zoneinfo import ZoneInfo

import discord
from discord.utils import escape_markdown, escape_mentions
import command_handler
from persistence.neighbor_db import connect
from persistence.rolodex import FF_GUILD, Rolodex
from persistence.rolodex_records import FIELDS, TABLES, add_event, edit_record, records
from persistence.rolodex_people import linked_accounts, link_accounts, notes, save_note, account_groups
from .rolodex_display import compact_profile, find_introduction

HELP = '''**Council Rolodex** — use a user mention or numeric ID, including departed users.
`$rolodex @user [page]` — neighborhood history, names, introduction and Council notes
`$rolodex note @user "text"` — add a Council note
`$rolodex note edit ID "text" "reason"` — revise/restore a note
`$rolodex note delete ID "reason"` — hide a note, retaining its history
`$rolodex link @old @new "reason"` — connect a confirmed account switch
`$rolodex unlink @old @new "reason"` — undo that account connection
`$rolodex accounts @user` — inspect connected IDs and active links
`$rolodex raw @user [page]` — every record with edit keys, including hidden incidents
`$rolodex review [page]` — unresolved reports and unparsed source messages
`$rolodex inspect event MESSAGE:LINE:EVENT` — full source evidence (EVENT starts at 0)
`$rolodex inspect membership ID` / `inspect name ID` / `inspect manual ID`
`$rolodex edit TYPE KEY FIELD "value" "reason"` — correct a record
`$rolodex reset TYPE KEY FIELD "reason"` — discard that field's correction, showing original evidence
`$rolodex add @user join FFC 2026-10-25 "reason / source link"` — add a missing neighborhood event (or leave)
`$rolodex audit [page]` — who changed what, when and why
Examples:
`$rolodex edit event 123456789012345678:1:0 user_id 355169964027805698 "Confirmed with member"`
`$rolodex edit membership 12 ended_at 2026-10-20 "Corrected date from ticket"`
`$rolodex edit event 123456789012345678:1:0 excluded true "Role assignment mistake"`
Use `null` for unknown dates, cleared names, or unresolved event user IDs.
Editable fields: membership: user_id, label, season, honorary, started_at, ended_at, excluded; name: user_id, value, excluded; event/manual: user_id, label, action, occurred_at, excluded.
Dates without a timezone use New York time. Corrections change Rolodex only, not Discord roles.'''


def text(value):
    return escape_mentions(escape_markdown(str(value))).replace('\n', ' ')


def uid(value):
    match = re.fullmatch(r'(?:<@!?(\d+)>|(\d+))', value)
    if not match or int(match[1] or match[2]) <= 0:
        raise ValueError('Use a user mention or numeric Discord ID; names may be ambiguous.')
    return int(match[1] or match[2])


def day(value):
    return datetime.fromisoformat(value).astimezone(ZoneInfo('America/New_York')).date().isoformat() if value else 'unknown'


def evidence(row):
    return f"https://discord.com/channels/{FF_GUILD}/{row['channel_id']}/{row['message_id']}"


def profile_lines(all_records, user_id, *, raw=False):
    selected = {kind: [r for r in rows if r['user_id'] == user_id and (raw or not r['excluded'])]
                for kind, rows in all_records.items()}
    if raw:
        lines = []
        for kind, rows in selected.items():
            for row in rows:
                fields = ', '.join(f'{f}={row.get(f)}' for f in sorted(FIELDS[kind]))
                lines.append(f"`{kind} {row['record_key']}` {text(fields)}")
        return lines or ['No records for this user.']
    return compact_profile(all_records, {user_id}, [])


async def send_page(context, title, lines, page=1, *, profile=False):
    # Bound each page by characters, including arbitrary imported text.
    pages, current = [], ''
    for line in lines:
        for start in range(0, max(1, len(line)), 1500):
            piece = line[start:start+1500] + '\n'
            if len(current) + len(piece) > 1700:
                pages.append(current)
                current = ''
            current += piece
    pages.append(current)
    if page < 1 or page > len(pages):
        raise ValueError(f'Page must be between 1 and {len(pages)}.')
    heading = f'# {title}' if profile else f'**{title}**'
    paging = f' — page {page}/{len(pages)}' if len(pages)>1 else ''
    await context.channel.send(content=f'{heading}{paging}\n{pages[page-1]}',
                               allowed_mentions=discord.AllowedMentions.none())


@command_handler.Command(access_type=command_handler.AccessType.PRIVILEGED,
                         desc='Council member history and audited corrections. Use $rolodex help.')
async def rolodex(activator, context):
    # Also guard direct calls; never rely on client-side visibility for editing rights.
    if context.guild is None or context.guild.id != FF_GUILD:
        return
    if context.access_type.value < command_handler.AccessType.PRIVILEGED.value:
        return
    args = context.args
    store = Rolodex()
    try:
        if not args or args[0] == 'help':
            await send_page(context, 'Rolodex help', HELP.splitlines(), int(args[1]) if len(args) > 1 else 1)
            return
        action = args[0].lower()
        actor_name = getattr(getattr(context, 'author', None), 'display_name', str(context.author_id))
        if action == 'note':
            if len(args) < 3:
                raise ValueError('Use $rolodex note @user "text", note edit ID "text" "reason", or note delete ID "reason".')
            if args[1] in ('edit','delete'):
                deleting = args[1] == 'delete'
                if len(args) < (4 if deleting else 5):
                    raise ValueError('Include the note ID, text (for edit), and a reason.')
                key = save_note(store, None, '' if deleting else args[3], context.author_id, actor_name,
                                note_id=int(args[2]), deleted=deleting,
                                reason=' '.join(args[3:] if deleting else args[4:]))
            else:
                key = save_note(store, uid(args[1]), ' '.join(args[2:]), context.author_id, actor_name)
            await send_page(context, 'Council note saved', [f'Note #{key}. Its revision history is retained in the audit.'])
            return
        if action in ('link','unlink'):
            if len(args) < 4:
                raise ValueError('Use $rolodex link @old @new "reason" (or unlink in the same old/new order).')
            key = link_accounts(store, uid(args[1]), uid(args[2]), context.author_id, actor_name,
                                ' '.join(args[3:]), active=action=='link')
            await send_page(context, 'Rolodex accounts updated', [f'Account change #{key} saved. XP and inventory are unchanged.'])
            return
        is_profile = False
        if action in ('edit', 'reset'):
            reset = action == 'reset'
            if len(args) < (5 if reset else 6):
                raise ValueError('Use $rolodex help for correction syntax; quote multiword values and reasons.')
            kind, key, field = args[1:4]
            value = None if reset or args[4].lower() == 'null' else args[4]
            reason = ' '.join(args[4:] if reset else args[5:])
            audit_id = edit_record(store, kind, key, field, value, context.author_id, reason, reset=reset)
            await send_page(context, 'Rolodex corrected', [f'Change #{audit_id} saved. Original evidence retained.'])
            return
        if action == 'add':
            if len(args) < 6:
                raise ValueError('Use: $rolodex add @user join FFC YYYY-MM-DD "reason / source"')
            key = add_event(store, uid(args[1]), args[2], args[3], args[4], context.author_id, ' '.join(args[5:]))
            await send_page(context, 'Rolodex event added', [f'Record `manual {key}` saved with your ID and reason.'])
            return
        with connect(store.path) as db:
            all_records = records(db)
            if action == 'audit':
                edits = [dict(r) for r in db.execute('SELECT * FROM rolodex_edit ORDER BY id DESC')]
                lines = [f"#{r['id']} {day(r['recorded_at'])} · actor {r['actor_id']} · {r['operation']} {r['record_type']} {r['record_key']} {r['field']}: {text(r['old_value'])} → {text(r['new_value'])} · {text(r['reason'])}" for r in edits]
                lines += [f"Added manual {r['id']} · actor {r['actor_id']} · {text(r['reason'])}" for r in all_records['manual']]
                for table in ('rolodex_note_revision','rolodex_account_link'):
                    lines += [text(json.dumps(dict(r), ensure_ascii=False)) for r in db.execute(f'SELECT * FROM {table} ORDER BY id DESC')]
                title, page = 'Rolodex audit', int(args[1]) if len(args)>1 else 1
            elif action == 'accounts':
                if len(args) != 2:
                    raise ValueError('Use $rolodex accounts @user')
                accounts = linked_accounts(db, uid(args[1]))
                lines = ['Connected Discord IDs: '+', '.join(str(x) for x in sorted(accounts))]
                lines += [f"{r['old_user_id']} → {r['new_user_id']} [linked by {text(r['actor_name'])}: {text(r['reason'])}]" for r in account_groups(db) if r['old_user_id'] in accounts]
                title, page = 'Rolodex accounts', 1
            elif action == 'inspect':
                if len(args) != 3:
                    raise ValueError('Use $rolodex inspect TYPE KEY')
                row = next((r for r in all_records.get(args[1], []) if r['record_key']==args[2]), None)
                if row is None:
                    raise ValueError('Record not found.')
                lines = ['Effective record: '+text(json.dumps(row, ensure_ascii=False))]
                if args[1] == 'event':
                    original = db.execute('SELECT * FROM membership_event WHERE message_id=? AND line_number=? AND event_number=?',
                                          (row['message_id'],row['line_number'],row['event_number'])).fetchone()
                else:
                    original = db.execute(f'SELECT * FROM {TABLES[args[1]]} WHERE id=?', (row['id'],)).fetchone()
                lines.append('Original record: '+text(json.dumps(dict(original), ensure_ascii=False)))
                if args[1] == 'event':
                    saved = db.execute('SELECT content FROM membership_log_message WHERE message_id=?', (row['message_id'],)).fetchone()
                    lines += [evidence(row), 'Original message: '+text(saved['content'])]
                title, page = 'Rolodex evidence', 1
            elif action == 'review':
                lines = [f"`event {r['record_key']}` {text(r['subject'])} {r['action']} {text(r['label'])} on {day(r['occurred_at'])}; suggested IDs {text(r['candidates'])} · {evidence(r)}" for r in all_records['event'] if r['user_id'] is None and not r['excluded']]
                from persistence.import_membership_history import LINE
                for row in db.execute('SELECT * FROM membership_log_message WHERE guild_id=? ORDER BY posted_at,message_id', (FF_GUILD,)):
                    for number, line in enumerate(row['content'].splitlines(), 1):
                        if line.strip() and not LINE.fullmatch(line.strip()):
                            lines.append(f"Unparsed {row['message_id']}:{number}: {text(line)} · {evidence(row)} — use add with this source link if appropriate.")
                title, page = 'Rolodex review', int(args[1]) if len(args)>1 else 1
            else:
                raw = action == 'raw'
                if raw and len(args)<2:
                    raise ValueError('Use $rolodex raw @user [page]')
                target = uid(args[1] if raw else args[0])
                index = 2 if raw else 1
                page = int(args[index]) if len(args)>index else 1
                accounts = linked_accounts(db, target)
                if raw:
                    lines = [f'Account {account}: {line}' for account in sorted(accounts)
                             for line in profile_lines(all_records, account, raw=True)]
                else:
                    lines = compact_profile(all_records, accounts, notes(db,accounts))
                    is_profile = True
                member = context.guild.get_member(target)
                saved_names = sorted((r for r in all_records['name'] if r['user_id'] in accounts and r['value'] and not r['excluded']), key=lambda r:(r['observed_at'],r['id']))
                display_name = member.display_name if member else saved_names[-1]['value'] if saved_names else str(target)
                title = f'{text(display_name)} Rolodex'
        if is_profile:
            introduction = await find_introduction(context.guild, accounts)
            lines = [line.replace('{introduction}',introduction) if line.startswith('**Link to introduction:**') else line for line in lines]
        await send_page(context, title, lines or ['No records to review.'], page, profile=is_profile)
    except (ValueError, TypeError) as error:
        await send_page(context, 'Rolodex', [text(error), 'Use $rolodex help for instructions.'])
