# Private ranked Council elections

Council can open an election with a configurable number of seats and nominees:

```
$election create "November Council election" 2 11/20/2026 8:00 PM @Alice @Bob @Carol
```

Use actual Discord user mentions for candidates. The title must be quoted.
Role mentions are also accepted, either alone or mixed with user mentions:

```
$election create "November Council election" 3 11/20/2026 8:00 PM @CandidateRole
```

Each role expands to all its current non-bot members, using a fresh server
member list. Overlapping roles and individually mentioned members are
deduplicated. There is no seven-candidate limit. The seat count must be a
positive integer, and there must be at least as many distinct candidates as
seats. The old syntax without a seat count still defaults to two seats, and
existing elections without that setting retain their original two seats.
Role changes after creation do not alter the candidates for that election.

The deadline uses fixed server time (UTC−4), including during winter.
Greg posts an election ID and instructions in the channel where it was opened.
Opening the election captures all current, non-bot members with the Council
role `648188387836166168` as its fixed eligible voter list. Later role changes
do not alter this election's voter list. The developer can administer elections
through the usual command permissions but must be on that list to vote.

## Voting

Greg immediately sends each eligible Council member a DM with a **Start /
continue voting** button when the election opens. That button opens the ballot
in the same DM, without a server command. The menu lets the voter choose candidates
one at a time in preference order, undo their last choice, and submit after
ranking at least as many candidates as the number of winning seats. For
example, three seats require three rankings. They may rank every candidate
they would accept. The
ballot has no tied or duplicate ranks. A draft does not count until submitted.
Lists larger than 25 remaining candidates use Previous/Next candidate pages
to fit Discord's dropdown limit. A Review full ranking button shows the entire
draft privately; the main menu previews the first ten choices for long ballots.

The submission creates a receipt message in the voter's conversation with
Greg. Receipts too long for a Discord message use a private text attachment
on that receipt, read and validated by Greg when counting. Submitting another
ballot for that election replaces the stored receipt
reference; exactly one submitted ballot per eligible Discord account is read
at closing. Earlier receipts remain in the DM but do not count. Receipt text
alone is not confirmation: the menu must also confirm successful submission.
Ballot text entered as an ordinary DM is not accepted; use the menu buttons.

Menus have no inactivity timeout and remain usable until voting closes. After
submission the same message has a **Change my vote** button. Every component
has a stable identifier for re-registration after a bot restart. Each draft
selection updates a private checkpoint in the DM message itself (or a private
attachment for a long draft), allowing the choices and candidate page to be
restored without storing rankings in the local database.

The election maintenance pass restores controls after a restart, normally on
its first run and at most the normal five-minute polling interval once the
existing automated jobs are running. On first upgrade it also scans each
voter's election-period DMs once, replacing old expiring ballot menus with the
durable entry button. Submitted receipt references are not changed. Older
unsubmitted drafts have no checkpoint and must be started again through the
button. Closed or expired elections are not reopened by this repair.

`$vote ID` remains an optional fallback that resends the invitation, rather
than a required part of normal voting. If DMs are blocked, the voter must
enable them before Greg can deliver the invitation.

## Unsubmitted ballots and reminders

Voters who have not submitted a ballot receive another DM menu after 24 hours,
then at most once per 24 hours until the deadline. Opening a menu or drafting
choices does not count as a submission. Submitted voters are skipped. The
same five-minute job that checks closing deadlines checks reminder eligibility;
reminders never extend the voting deadline and stop on cancellation/closing.

Invitation/reminder attempts are stored in the election database, so a restart
does not reset the reminder clock or resend invitations to everyone. Blocked
or failed DM deliveries are retried no more than daily and do not interrupt
delivery to other members. Election creation reports initial delivery totals.
`$election status ID` lists voters still awaiting a ballot and flags blocked
or failed DM deliveries, without showing any rankings. These lists suppress
mentions; they do not automatically ping Council in the server.

## Counting

The deadline is enforced when submitting, even if the automatic counter runs
a little later. A five-minute background job closes due elections and also
processes overdue elections after a restart. Council can close early with
`$election close ID`; this freezes the cutoff at that time. No further ballots
are accepted while counting or after closing. A failed receipt fetch can be
retried without moving the original cutoff or dropping the ballot.

Counting uses the configured number of seats, a fixed Droop quota
`floor(valid ballots / (seats + 1)) + 1`, and weighted inclusive Gregory surplus
transfers. It uses exact rational arithmetic, rounding only for display.
Each ballot begins with weight one. At each round it supports its highest
ranked continuing candidate. A candidate reaching the quota is elected and
each of their ballots transfers its current weight multiplied by
`(candidate total - quota) / candidate total`. Votes with no remaining
ranked candidate are exhausted; the quota does not change.

When no candidate reaches the quota, the weakest candidate is eliminated.
If all remaining candidates fit into the remaining seats, they are elected
even below quota. No ballots means no seats filled.

Tied final-seat candidates are reported, with the seat left unfilled for a
Senior Council winner vote. Earlier elimination ties use this order:

1. Compare previous-round totals, most recent first. The weaker historical
   total is eliminated; candidates still exactly tied move to the next step.
2. Compare Borda-style scores from the original valid ballots at full weight.
   With N original nominees, first place earns N−1 points, second N−2, down
   to zero for last place. Unranked nominees get zero. Only the remaining
   tied elimination candidates are compared; the lowest score is eliminated.
3. If the lowest Borda scores also tie, stop and request a Senior Council
   decision. The result lists the precise eligible elimination choices, as
   well as all still-contending candidates.

Record the Senior Council's selected elimination with
`$election eliminate ID @nominee` (a numeric Discord user ID is also accepted).
This is an attestation by the privileged Council member issuing the command;
Greg does not independently collect or verify the Senior Council's vote.
Only a nominee in the currently unresolved elimination tie can be selected.
Greg records the elimination round, selected nominee, recorder's ID, and
timestamp, rereads the same frozen private receipts, and continues counting.
If another unresolved elimination tie occurs, another decision can be recorded.
Previous decisions are reproduced on subsequent recounts and appear in the
round report. A missing/unreadable receipt or invalid decision stops the
recount without silently dropping a ballot or committing the new decision.

Zero-vote candidates tied for elimination can still be removed together when
enough candidates remain to fill all seats. Nonzero tied candidates are not
batch-eliminated. Final winner ties do not use the Borda elimination rule or
the elimination command; those remain for a Senior Council winner vote.
There are no random or alphabetical tie-breaks that determine who wins.
The Senior Member follow-up election is not started automatically.

## Administration and results

- `$election help` — syntax and rules.
- `$election list` — recent elections.
- `$election status ID` — settings and aggregate turnout, without interim tallies.
- `$election close ID` — freeze voting early, count, and post the result.
- `$election results ID` — retrieve a saved aggregate result.
- `$election rounds ID` — view candidate totals, actions, transfers, and exhausted
  vote weights for each counting round, including tie-break scores and decisions.
- `$election recount ID` — apply the current counting rules to an already
  closed election's original ballots. This can apply Borda tie-breaks to an
  election previously stopped under the older rules.
- `$election eliminate ID @nominee` — record the Senior Council's chosen
  elimination and resume a pending elimination tie.
- `$election cancel ID` — cancel an open election without counting it.

These administrative commands use the existing privileged access checks.
Recounting and recording decisions never reopen voting or change its cutoff.
They publish an **Updated results** announcement and increment its revision;
the saved result retrieved by `$election results ID` is always the latest one.
Only `$vote` is public, with its own fixed-voter-list check. The result is sent
to the election's original channel. Messages suppress mentions. No interim
candidate tallies or individual ballots are shown to Council. If result
delivery has an uncertain outcome, it is retained as pending instead of
automatically posting a duplicate; the saved result remains available through
`$election results ID`.

## Storage and privacy

Feature code lives in `commands/council_election.py`, `election_count.py`, and
`election_store.py`, plus `election_recovery.py` for restart/legacy-menu repair,
with small registration wrappers in `commands/commands.py`.
It uses Discord's DM interaction menus; no changes to `custom_types.py`,
`command_handler.py`, `responses.py`, or `greg3.py` are required.

`data/council_elections.sqlite3` stores election settings, eligibility, each
voter's DM/receipt message IDs and submission timestamp, menu message references,
delivery/repair status, Senior Council elimination decisions, and aggregate results. It does **not** store individual
rankings. Submitted ballots and unfinished drafts remain in bot-authored Discord
DM messages or their attachments, are loaded temporarily into memory, and are not
written to logs. A voter cannot change their submitted ranking by editing
their own messages. Only explicit menu submissions replace the vote reference.

This is private voting, not anonymity from the operator of Greg or Discord:
someone controlling the bot can access its DMs. Aggregate rounds can also
reveal preferences in a small electorate. DM receipts are retained on Discord,
including after cancellation; cancelling does not delete them.
