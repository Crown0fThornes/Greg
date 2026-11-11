# Private ranked Council elections

Council can open a two-seat election with two to seven distinct candidates:

```
$election create "November Council election" 11/20/2026 8:00 PM @Alice @Bob @Carol
```

Use actual Discord user mentions for candidates. The title must be quoted.
Role mentions are also accepted, either alone or mixed with user mentions:

```
$election create "November Council election" 11/20/2026 8:00 PM @CandidateRole
```

Each role expands to all its current non-bot members, using a fresh server
member list. Overlapping roles and individually mentioned members are
deduplicated. The expanded candidate list must contain two to seven people;
an oversized or undersized list is rejected rather than silently truncated.
Role changes after creation do not alter the candidates for that election.

The deadline uses fixed server time (UTC−4), including during winter.
Greg posts an election ID and instructions in the channel where it was opened.
Opening the election captures all current, non-bot members with the Council
role `648188387836166168` as its fixed eligible voter list. Later role changes
do not alter this election's voter list. The developer can administer elections
through the usual command permissions but must be on that list to vote.

## Voting

Greg immediately sends each eligible Council member a private DM ballot when
the election opens. If someone needs another menu, they can run `$vote ID` in
the server; that server request receives a ✅. The menu lets the voter choose candidates
one at a time in preference order, undo their last choice, and submit after
ranking at least two. They may rank every candidate they would accept. The
ballot has no tied or duplicate ranks. A draft does not count until submitted.

The submission creates a receipt message in the voter's conversation with
Greg. Submitting another ballot for that election replaces the stored receipt
reference; exactly one submitted ballot per eligible Discord account is read
at closing. Earlier receipts remain in the DM but do not count. Receipt text
alone is not confirmation: the menu must also confirm successful submission.
Ballot text entered as an ordinary DM is not accepted; use the menu buttons.

Menus expire after ten minutes. After expiry or a bot restart, run `$vote ID`
again in the server for a new menu. Already submitted ballots survive restarts.
If DMs are blocked, Greg asks the voter to enable them and retry.

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

Counting uses exactly two seats, a fixed Droop quota
`floor(valid ballots / 3) + 1`, and weighted inclusive Gregory surplus
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
Senior Member vote. Earlier elimination ties compare the tied candidates'
totals in previous rounds, most recent first. If those also tie, counting
stops and reports all still-contending candidates and the tied elimination,
so nobody is eliminated arbitrarily. Zero-vote candidates tied for elimination
can be removed together. Nonzero tied candidates are not batch-eliminated.
There are no random or alphabetical tie-breaks that determine who wins.
The Senior Member follow-up election is not started automatically.

## Administration and results

- `$election help` — syntax and rules.
- `$election list` — recent elections.
- `$election status ID` — settings and aggregate turnout, without interim tallies.
- `$election close ID` — freeze voting early, count, and post the result.
- `$election results ID` — retrieve a saved aggregate result.
- `$election rounds ID` — view candidate totals, actions, transfers, and exhausted
  vote weights for each counting round.
- `$election cancel ID` — cancel an open election without counting it.

These administrative commands use the existing privileged access checks.
Only `$vote` is public, with its own fixed-voter-list check. The result is sent
to the election's original channel. Messages suppress mentions. No interim
candidate tallies or individual ballots are shown to Council. If result
delivery has an uncertain outcome, it is retained as pending instead of
automatically posting a duplicate; the saved result remains available through
`$election results ID`.

## Storage and privacy

Feature code lives in `commands/council_election.py`, `election_count.py`, and
`election_store.py`, with small registration wrappers in `commands/commands.py`.
It uses Discord's DM interaction menus; no changes to `custom_types.py`,
`command_handler.py`, `responses.py`, or `greg3.py` are required.

`data/council_elections.sqlite3` stores election settings, eligibility, each
voter's DM/receipt message IDs and submission timestamp, and aggregate results.
It does **not** store individual rankings. Those remain in bot-authored Discord
DM receipts, are loaded temporarily into memory for counting, and are not
written to logs. A voter cannot change their submitted ranking by editing
their own messages. Only explicit menu submissions replace the vote reference.

This is private voting, not anonymity from the operator of Greg or Discord:
someone controlling the bot can access its DMs. Aggregate rounds can also
reveal preferences in a small electorate. DM receipts are retained on Discord,
including after cancellation; cancelling does not delete them.
