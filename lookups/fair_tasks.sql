CREATE TABLE fair_task_completions (
    member_id INTEGER NOT NULL,
    task_num INTEGER NOT NULL,

    PRIMARY KEY (member_id, task_num)
);

CREATE TABLE fair_task_submissions (
    member_id INTEGER NOT NULL,
    task_num INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,

    PRIMARY KEY (member_id, task_num, channel_id, message_id)
);