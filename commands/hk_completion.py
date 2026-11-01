"""One Council-role follow-up for an HK task unchecked after 24 hours."""
import logging
import discord

log=logging.getLogger(__name__)


async def completion_followups(guild,delivery,neighborhoods,now):
    with delivery.connection() as db:
        db.execute('CREATE TABLE IF NOT EXISTS completion_followup '
                   '(nh INTEGER,ping_id INTEGER,status TEXT NOT NULL,followup_id INTEGER,'
                   'PRIMARY KEY(nh,ping_id))')
        rows=db.execute("SELECT d.emoji_id,d.discord_message_id FROM delivery d "
                        'LEFT JOIN completion_followup f ON f.nh=d.emoji_id AND f.ping_id=d.discord_message_id '
                        "WHERE d.part=0 AND d.status='sent' AND d.sent_at<=? AND f.ping_id IS NULL "
                        'ORDER BY d.sent_at LIMIT 100',(now.timestamp()-86400,)).fetchall()
    for nh,ping_id in rows:
        if nh not in neighborhoods:
            continue
        channel_id,role_id=neighborhoods[nh]
        try:
            channel=await guild.fetch_channel(channel_id)
            try:
                message=await channel.fetch_message(ping_id)
            except discord.NotFound:
                with delivery.connection() as db:
                    db.execute("INSERT OR IGNORE INTO completion_followup VALUES (?,?,'missing',NULL)",(nh,ping_id))
                continue
            completed=False
            for reaction in message.reactions:
                if str(reaction.emoji)=='✅':
                    async for user in reaction.users():
                        if not user.bot:
                            completed=True
                            break
            with delivery.connection() as db:
                claimed=db.execute('INSERT OR IGNORE INTO completion_followup VALUES (?,?,?,NULL)',
                                   (nh,ping_id,'completed' if completed else 'pending')).rowcount
            if completed or not claimed:
                continue
            title=discord.utils.escape_mentions(message.content.splitlines()[0])[:250]
            content=(f'**HK task follow-up**\n<@&{role_id}>\n'
                     f'No one has marked this task complete after 24 hours: {title}\n'
                     'Please check on it and react with ✅ on the original task ping when complete.\n\n'
                     f'Original ping: https://discord.com/channels/{guild.id}/{channel_id}/{ping_id}')
            try:
                sent=await channel.send(content,allowed_mentions=discord.AllowedMentions(
                    everyone=False,users=False,roles=[discord.Object(id=role_id)],replied_user=False))
            except (discord.Forbidden,discord.NotFound):
                # Definite rejection: allow a later attempt after permissions are fixed.
                with delivery.connection() as db:
                    db.execute('DELETE FROM completion_followup WHERE nh=? AND ping_id=?',(nh,ping_id))
                raise
            except Exception:
                log.exception('HK completion follow-up delivery uncertain for NH %s, ping %s',nh,ping_id)
                continue
            with delivery.connection() as db:
                db.execute("UPDATE completion_followup SET status='sent',followup_id=? WHERE nh=? AND ping_id=?",
                           (sent.id,nh,ping_id))
        except discord.HTTPException:
            log.exception('Could not check HK completion for NH %s, ping %s',nh,ping_id)
