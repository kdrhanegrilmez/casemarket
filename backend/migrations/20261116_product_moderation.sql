BEGIN;

ALTER TABLE products ADD COLUMN IF NOT EXISTS admin_hidden_at TIMESTAMPTZ;
ALTER TABLE products ADD COLUMN IF NOT EXISTS admin_hidden_by BIGINT REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE products ADD COLUMN IF NOT EXISTS admin_hidden_reason TEXT;

CREATE TABLE IF NOT EXISTS seller_notifications (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    recipient_user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    actor_user_id BIGINT NOT NULL REFERENCES users(id),
    product_id BIGINT NOT NULL REFERENCES products(id),
    kind VARCHAR(40) NOT NULL CHECK (kind IN ('product_removed_by_admin')),
    reason TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    read_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_seller_notifications_recipient
ON seller_notifications(recipient_user_id, created_at DESC);

COMMIT;
