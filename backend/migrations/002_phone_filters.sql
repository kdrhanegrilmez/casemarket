
BEGIN;

-- 1. TELEFON MARKALARI
CREATE TABLE IF NOT EXISTS phone_brands (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(60) NOT NULL UNIQUE
);


-- 2. TELEFON MODELLERI
CREATE TABLE IF NOT EXISTS phone_models (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    brand_id BIGINT NOT NULL
        REFERENCES phone_brands(id) ON DELETE RESTRICT,

    name VARCHAR(100) NOT NULL,

    UNIQUE (brand_id, name)
);


-- 3. URUNLERIN UYUMLU OLDUGU TELEFON MODELLERI
CREATE TABLE IF NOT EXISTS product_compatible_models (
    product_id BIGINT NOT NULL
        REFERENCES products(id) ON DELETE CASCADE,

    phone_model_id BIGINT NOT NULL
        REFERENCES phone_models(id) ON DELETE RESTRICT,

    PRIMARY KEY (product_id, phone_model_id)
);


-- 4. FILTRELEME ICIN INDEXLER
CREATE INDEX IF NOT EXISTS idx_phone_models_brand
    ON phone_models(brand_id);

CREATE INDEX IF NOT EXISTS idx_product_compatible_models_model
    ON product_compatible_models(phone_model_id);


-- 5. KILIF TURLERI
-- categories tablosu projede zaten mevcut.
INSERT INTO categories (name)
VALUES
    ('Cüzdan Kılıf'),
    ('Silikon Kılıf'),
    ('Şeffaf Kılıf'),
    ('Desenli Kılıf'),
    ('Standlı Kılıf'),
    ('Darbeye Dayanıklı Kılıf')
ON CONFLICT (name) DO NOTHING;


-- 6. ORNEK TELEFON MARKALARI
INSERT INTO phone_brands (name)
VALUES
    ('Apple'),
    ('Samsung'),
    ('Xiaomi'),
    ('Google')
ON CONFLICT (name) DO NOTHING;


-- 7. ORNEK TELEFON MODELLERI
WITH models(brand_name, model_name) AS (
    VALUES
        ('Apple', 'iPhone 13'),
        ('Apple', 'iPhone 14'),
        ('Apple', 'iPhone 15'),
        ('Apple', 'iPhone 15 Pro'),
        ('Apple', 'iPhone 16'),
        ('Apple', 'iPhone 16 Pro'),

        ('Samsung', 'Galaxy S23'),
        ('Samsung', 'Galaxy S24'),
        ('Samsung', 'Galaxy S24 Ultra'),
        ('Samsung', 'Galaxy A54'),
        ('Samsung', 'Galaxy A55'),

        ('Xiaomi', 'Redmi Note 13'),
        ('Xiaomi', 'Redmi Note 13 Pro'),

        ('Google', 'Pixel 8'),
        ('Google', 'Pixel 9')
)
INSERT INTO phone_models (brand_id, name)
SELECT
    b.id,
    m.model_name
FROM models AS m
JOIN phone_brands AS b
    ON b.name = m.brand_name
ON CONFLICT (brand_id, name) DO NOTHING;

COMMIT;
