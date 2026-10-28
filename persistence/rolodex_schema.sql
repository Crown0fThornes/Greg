CREATE TABLE IF NOT EXISTS person (
    user_id INTEGER PRIMARY KEY CHECK(user_id > 0)
);
-- A NULL value is meaningful: e.g. a nickname was cleared.
CREATE TABLE IF NOT EXISTS name_history (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES person(user_id),
    guild_id INTEGER NOT NULL DEFAULT 0,
    kind TEXT NOT NULL CHECK(kind IN ('username', 'global_name', 'nickname')),
    value TEXT,
    observed_at TEXT NOT NULL,
    source TEXT NOT NULL CHECK(source IN ('observation', 'gateway'))
);
CREATE INDEX IF NOT EXISTS names_by_person ON name_history(user_id, guild_id, kind, id);
CREATE TABLE IF NOT EXISTS membership (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES person(user_id),
    guild_id INTEGER NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('server', 'neighborhood', 'family')),
    membership_key TEXT NOT NULL,
    label TEXT NOT NULL,
    season INTEGER,
    honorary INTEGER NOT NULL DEFAULT 0 CHECK(honorary IN (0, 1)),
    role_id INTEGER,
    started_at TEXT,
    first_observed_at TEXT NOT NULL,
    ended_at TEXT,
    end_observed_at TEXT,
    start_source TEXT NOT NULL CHECK(start_source IN ('observation', 'gateway', 'discord_joined_at')),
    end_source TEXT CHECK(end_source IN ('observation', 'gateway'))
);
CREATE UNIQUE INDEX IF NOT EXISTS one_open_membership
    ON membership(user_id, guild_id, kind, membership_key) WHERE end_observed_at IS NULL;
CREATE INDEX IF NOT EXISTS memberships_by_person ON membership(user_id, guild_id, id);
-- Source messages are retained even when their wording cannot be parsed.
CREATE TABLE IF NOT EXISTS membership_log_message (
    message_id INTEGER PRIMARY KEY,
    guild_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    author_id INTEGER NOT NULL,
    posted_at TEXT NOT NULL,
    content TEXT NOT NULL,
    imported_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS membership_event (
    id INTEGER PRIMARY KEY,
    message_id INTEGER NOT NULL REFERENCES membership_log_message(message_id),
    line_number INTEGER NOT NULL,
    event_number INTEGER NOT NULL,
    user_id INTEGER REFERENCES person(user_id),
    subject TEXT NOT NULL,
    action TEXT NOT NULL CHECK(action IN ('join', 'leave')),
    kind TEXT NOT NULL CHECK(kind IN ('neighborhood', 'server')),
    label TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    resolution TEXT NOT NULL,
    candidates TEXT NOT NULL DEFAULT '[]',
    UNIQUE(message_id, line_number, event_number)
);
CREATE INDEX IF NOT EXISTS membership_events_by_person
    ON membership_event(user_id, occurred_at, id);
CREATE TABLE IF NOT EXISTS rolodex_manual_event (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES person(user_id),
    guild_id INTEGER NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('neighborhood','server','family')),
    label TEXT NOT NULL,
    action TEXT NOT NULL CHECK(action IN ('join','leave')),
    occurred_at TEXT NOT NULL,
    actor_id INTEGER NOT NULL,
    reason TEXT NOT NULL,
    recorded_at TEXT NOT NULL
);
-- Append-only corrections overlay evidence; original records stay untouched.
CREATE TABLE IF NOT EXISTS rolodex_edit (
    id INTEGER PRIMARY KEY,
    record_type TEXT NOT NULL,
    record_key TEXT NOT NULL,
    field TEXT NOT NULL,
    operation TEXT NOT NULL CHECK(operation IN ('set','reset')),
    old_value TEXT NOT NULL,
    new_value TEXT NOT NULL,
    actor_id INTEGER NOT NULL,
    reason TEXT NOT NULL,
    recorded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS rolodex_edits_by_record ON rolodex_edit(record_type,record_key,id);
CREATE TABLE IF NOT EXISTS rolodex_note_revision (
    id INTEGER PRIMARY KEY,
    note_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL REFERENCES person(user_id),
    body TEXT NOT NULL,
    deleted INTEGER NOT NULL DEFAULT 0 CHECK(deleted IN (0,1)),
    actor_id INTEGER NOT NULL,
    actor_name TEXT NOT NULL,
    reason TEXT NOT NULL,
    recorded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS rolodex_note_versions ON rolodex_note_revision(note_id,id);
CREATE TABLE IF NOT EXISTS rolodex_account_link (
    id INTEGER PRIMARY KEY,
    old_user_id INTEGER NOT NULL REFERENCES person(user_id),
    new_user_id INTEGER NOT NULL REFERENCES person(user_id),
    active INTEGER NOT NULL CHECK(active IN (0,1)),
    actor_id INTEGER NOT NULL,
    actor_name TEXT NOT NULL,
    reason TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    CHECK(old_user_id != new_user_id)
);
