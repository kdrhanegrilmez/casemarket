BEGIN;

CREATE TABLE IF NOT EXISTS support_threads (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kind VARCHAR(30) NOT NULL CHECK (kind IN (
        'customer_support', 'seller_support', 'product_question', 'product_moderation'
    )),
    customer_user_id BIGINT REFERENCES users(id),
    seller_user_id BIGINT REFERENCES users(id),
    product_id BIGINT REFERENCES products(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (
        (kind = 'customer_support' AND customer_user_id IS NOT NULL AND seller_user_id IS NULL AND product_id IS NULL)
        OR (kind = 'seller_support' AND seller_user_id IS NOT NULL AND customer_user_id IS NULL AND product_id IS NULL)
        OR (kind = 'product_question' AND customer_user_id IS NOT NULL AND seller_user_id IS NOT NULL AND product_id IS NOT NULL)
        OR (kind = 'product_moderation' AND seller_user_id IS NOT NULL AND customer_user_id IS NULL AND product_id IS NOT NULL)
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_support_customer_thread
ON support_threads(customer_user_id) WHERE kind = 'customer_support';
CREATE UNIQUE INDEX IF NOT EXISTS idx_support_seller_thread
ON support_threads(seller_user_id) WHERE kind = 'seller_support';
CREATE UNIQUE INDEX IF NOT EXISTS idx_support_question_thread
ON support_threads(customer_user_id, product_id) WHERE kind = 'product_question';
CREATE UNIQUE INDEX IF NOT EXISTS idx_support_moderation_thread
ON support_threads(product_id) WHERE kind = 'product_moderation';
CREATE INDEX IF NOT EXISTS idx_support_threads_seller
ON support_threads(seller_user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_support_threads_updated
ON support_threads(updated_at DESC);

CREATE TABLE IF NOT EXISTS support_messages (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    thread_id BIGINT NOT NULL REFERENCES support_threads(id) ON DELETE CASCADE,
    sender_user_id BIGINT NOT NULL REFERENCES users(id),
    body VARCHAR(2000) NOT NULL CHECK (length(trim(body)) > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_support_messages_thread
ON support_messages(thread_id, id);

-- Sohbet özelliğinden önce admin tarafından kaldırılmış ürünleri konuşmaya taşı.
INSERT INTO support_threads (kind, seller_user_id, product_id, created_at, updated_at)
SELECT 'product_moderation', s.owner_user_id, p.id, p.admin_hidden_at, p.admin_hidden_at
FROM products AS p
JOIN sellers AS s ON s.id = p.seller_id
WHERE p.admin_hidden_at IS NOT NULL
ON CONFLICT DO NOTHING;

INSERT INTO support_messages (thread_id, sender_user_id, body, created_at)
SELECT t.id, p.admin_hidden_by,
       'Ürün #' || p.id || ' yayından kaldırıldı. Gerekçe: ' ||
       COALESCE(p.admin_hidden_reason, 'Gerekçe belirtilmedi.'),
       p.admin_hidden_at
FROM support_threads AS t
JOIN products AS p ON p.id = t.product_id
WHERE t.kind = 'product_moderation'
  AND p.admin_hidden_at IS NOT NULL
  AND p.admin_hidden_by IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM support_messages AS m WHERE m.thread_id = t.id);

COMMIT;
