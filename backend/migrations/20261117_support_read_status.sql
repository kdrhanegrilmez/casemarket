ALTER TABLE support_threads
    ADD COLUMN IF NOT EXISTS status VARCHAR(10) NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'closed')),
    ADD COLUMN IF NOT EXISTS closed_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS support_thread_reads (
    thread_id BIGINT NOT NULL REFERENCES support_threads(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    last_read_message_id BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (thread_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_support_messages_sender_created
ON support_messages(sender_user_id, created_at);
