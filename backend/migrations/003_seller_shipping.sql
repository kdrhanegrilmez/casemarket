ALTER TABLE order_items
    ADD COLUMN IF NOT EXISTS shipping_status VARCHAR(20) NOT NULL DEFAULT 'pending'
    CHECK (shipping_status IN ('pending', 'preparing', 'shipped', 'delivered'));

CREATE INDEX IF NOT EXISTS idx_order_items_seller_order ON order_items(seller_id, order_id);
