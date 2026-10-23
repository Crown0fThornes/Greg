-- A player's progress belongs to a Discord server, not an animal family.
CREATE TABLE IF NOT EXISTS neighbor (
    user_id INTEGER NOT NULL CHECK (user_id > 0),
    guild_id INTEGER NOT NULL CHECK (guild_id > 0),
    xp INTEGER NOT NULL DEFAULT 0,
    legacy_xp INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, guild_id)
);

-- Each row is an owned item instance. Duplicate names/types are allowed.
CREATE TABLE IF NOT EXISTS item (
    item_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    guild_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    -- Unix seconds; nonpositive values mean no expiration, as in Item today.
    expiration INTEGER NOT NULL DEFAULT -1,
    inventory_position INTEGER NOT NULL CHECK (inventory_position >= 0),
    FOREIGN KEY (user_id, guild_id)
        REFERENCES neighbor (user_id, guild_id) ON DELETE CASCADE,
    UNIQUE (user_id, guild_id, inventory_position)
);

CREATE INDEX IF NOT EXISTS item_owner_name ON item (user_id, guild_id, name);
CREATE INDEX IF NOT EXISTS item_owner_type ON item (user_id, guild_id, type);

-- Values are text, matching the values returned by the existing Item decoder.
CREATE TABLE IF NOT EXISTS item_attribute (
    item_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    value TEXT NOT NULL,
    PRIMARY KEY (item_id, name),
    FOREIGN KEY (item_id) REFERENCES item (item_id) ON DELETE CASCADE
);
