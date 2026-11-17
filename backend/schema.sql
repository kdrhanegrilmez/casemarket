CREATE table IF NOT EXISTS users(
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    full_name VARCHAR(120) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,

    role VARCHAR(20) NOT NULL DEFAULT 'customer'
        CHECK (role IN('customer', 'seller', 'admin')),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sellers(
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    owner_user_id BIGINT NOT NULl UNIQUE
                                  REFERENCES users(id), --foreign key yaptık
    store_name VARCHAR(120) NOT NULL,
    description TEXT,
    approval_status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CONSTRAINT sellers_approval_status_check
        CHECK (approval_status IN ('pending', 'approved', 'rejected')),
    reviewed_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ,
    review_reason TEXT,
    commission_rate_percent NUMERIC(5, 2)
        CONSTRAINT sellers_commission_rate_check
        CHECK (commission_rate_percent IS NULL OR
               commission_rate_percent BETWEEN 0 AND 100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()

);

CREATE INDEX IF NOT EXISTS idx_sellers_approval_status ON sellers(approval_status);

CREATE TABLE IF NOT EXISTS admin_audit_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor_user_id BIGINT NOT NULL REFERENCES users(id),
    action VARCHAR(80) NOT NULL,
    target_type VARCHAR(40) NOT NULL,
    target_id BIGINT NOT NULL,
    before_data JSONB,
    after_data JSONB,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_admin_audit_logs_target
ON admin_audit_logs(target_type, target_id);

CREATE INDEX IF NOT EXISTS idx_admin_audit_logs_created_at
ON admin_audit_logs(created_at DESC);

--Ürün kategorileri


CREATE TABLE IF NOT EXISTS categories(
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);



-- Satıcıların ürünleri tablosu
CREATE TABLE IF NOT EXISTS products (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    seller_id BIGINT NOT NULL
        REFERENCES sellers(id),

    category_id BIGINT
        REFERENCES categories(id),

    name VARCHAR(150) NOT NULL,

    description TEXT,

    price NUMERIC(10, 2) NOT NULL
        CHECK (price > 0),

    stock INTEGER NOT NULL DEFAULT 0
        CHECK (stock >= 0),

    image_url TEXT,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    admin_hidden_at TIMESTAMPTZ,
    admin_hidden_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    admin_hidden_reason TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

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

CREATE TABLE IF NOT EXISTS support_threads (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kind VARCHAR(30) NOT NULL CHECK (kind IN (
        'customer_support', 'seller_support', 'product_question', 'product_moderation'
    )),
    customer_user_id BIGINT REFERENCES users(id),
    seller_user_id BIGINT REFERENCES users(id),
    product_id BIGINT REFERENCES products(id),
    status VARCHAR(10) NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'closed')),
    closed_at TIMESTAMPTZ,
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
CREATE INDEX IF NOT EXISTS idx_support_messages_sender_created
ON support_messages(sender_user_id, created_at);

CREATE TABLE IF NOT EXISTS support_thread_reads (
    thread_id BIGINT NOT NULL REFERENCES support_threads(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    last_read_message_id BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (thread_id, user_id)
);

--Müşteri siparişleri
CREATE TABLE IF NOT EXISTS orders (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id BIGINT NOT NULL
                                  REFERENCES users(id),
    total_amount NUMERIC(10,2) NOT NULL
                                    CHECK (total_amount >= 0),
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
                                    CHECK(status IN ('pending', 'paid','canceled')),

    shipping_address TEXT,
    payment_method_summary VARCHAR(80),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

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

--Siparişin içindeki ürünler

CREATE TABLE IF NOT EXISTS order_items (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    order_id BIGINT NOT NULL
        REFERENCES orders(id),

    product_id BIGINT NOT NULL
        REFERENCES products(id),

    seller_id BIGINT NOT NULL
        REFERENCES sellers(id),

    product_name VARCHAR(150) NOT NULL,

    quantity INTEGER NOT NULL
        CHECK (quantity > 0),

    unit_price NUMERIC(10, 2) NOT NULL
        CHECK (unit_price > 0),

    shipping_status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (shipping_status IN ('pending', 'preparing', 'shipped', 'delivered'))
);

CREATE INDEX IF NOT EXISTS idx_order_items_seller_order ON order_items(seller_id, order_id);
