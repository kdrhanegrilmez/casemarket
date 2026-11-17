ALTER TABLE order_items
    ADD COLUMN IF NOT EXISTS shipping_company VARCHAR(100),
    ADD COLUMN IF NOT EXISTS tracking_number VARCHAR(100);
