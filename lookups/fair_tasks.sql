CREATE TABLE fair_tasks (
    neighbor_ID INTEGER PRIMARY KEY,

    -- Set 1
    helpful_neighbor INTEGER NOT NULL DEFAULT 0 CHECK (helpful_neighbor IN (0, 1)),
    derby_req INTEGER NOT NULL DEFAULT 0 CHECK (derby_req IN (0, 1)),
    pet_pics INTEGER NOT NULL DEFAULT 0 CHECK (pet_pics IN (0, 1)),
    historian INTEGER NOT NULL DEFAULT 0 CHECK (historian IN (0, 1)),
    culture INTEGER NOT NULL DEFAULT 0 CHECK (culture IN (0, 1)),
    copy_cats INTEGER NOT NULL DEFAULT 0 CHECK (copy_cats IN (0, 1)),
    active_player INTEGER NOT NULL DEFAULT 0 CHECK (active_player IN (0, 1)),
    a_lincoln_classic INTEGER NOT NULL DEFAULT 0 CHECK (a_lincoln_classic IN (0, 1)),

    -- Set 2
    farm_design INTEGER NOT NULL DEFAULT 0 CHECK (farm_design IN (0, 1)),
    carrots_to_carrots INTEGER NOT NULL DEFAULT 0 CHECK (carrots_to_carrots IN (0, 1)),
    fair_vendor INTEGER NOT NULL DEFAULT 0 CHECK (fair_vendor IN (0, 1)),
    farm_and_chat INTEGER NOT NULL DEFAULT 0 CHECK (farm_and_chat IN (0, 1)),
    moody INTEGER NOT NULL DEFAULT 0 CHECK (moody IN (0, 1)),
    pride_annex INTEGER NOT NULL DEFAULT 0 CHECK (pride_annex IN (0, 1)),
    meet_the_neighbors INTEGER NOT NULL DEFAULT 0 CHECK (meet_the_neighbors IN (0, 1)),
    nurture INTEGER NOT NULL DEFAULT 0 CHECK (nurture IN (0, 1)),

    -- Set 3
    boat_week INTEGER NOT NULL DEFAULT 0 CHECK (boat_week IN (0, 1)),
    feedback INTEGER NOT NULL DEFAULT 0 CHECK (feedback IN (0, 1)),
    stimulate_local_economy INTEGER NOT NULL DEFAULT 0 CHECK (stimulate_local_economy IN (0, 1)),
    wordle_wizard INTEGER NOT NULL DEFAULT 0 CHECK (wordle_wizard IN (0, 1)),
    gratitude INTEGER NOT NULL DEFAULT 0 CHECK (gratitude IN (0, 1)),
    what_ifs_challenge INTEGER NOT NULL DEFAULT 0 CHECK (what_ifs_challenge IN (0, 1)),
    peasant_havens_challenge INTEGER NOT NULL DEFAULT 0 CHECK (peasant_havens_challenge IN (0, 1)),
    citizen_science INTEGER NOT NULL DEFAULT 0 CHECK (citizen_science IN (0, 1))
);