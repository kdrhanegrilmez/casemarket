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
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()

);

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

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
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
        CHECK (unit_price > 0)
);
