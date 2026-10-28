-- Mevcut veritabanına bir kez uygulanır: psql ... -f backend/migrations/001_account_checkout.sql
ALTER TABLE orders ADD COLUMN IF NOT EXISTS shipping_address TEXT;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS payment_method_summary VARCHAR(80);

CREATE TABLE IF NOT EXISTS user_addresses (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    label VARCHAR(60) NOT NULL,
    recipient VARCHAR(120) NOT NULL,
    phone VARCHAR(30) NOT NULL,
    city VARCHAR(80) NOT NULL,
    district VARCHAR(80) NOT NULL,
    address_line TEXT NOT NULL,
    postal_code VARCHAR(12),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_payment_methods (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    label VARCHAR(60) NOT NULL,
    brand VARCHAR(30) NOT NULL,
    last_four CHAR(4) NOT NULL CHECK (last_four ~ '^[0-9]{4}$'),
    expiry_month INTEGER NOT NULL CHECK (expiry_month BETWEEN 1 AND 12),
    expiry_year INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
