
BEGIN;

-- ==========================================
-- 1. MAGAZA BASVURU VE ONAY DURUMU
-- ==========================================

-- Mevcut magazalari kaybetmeden yeni alani ekle.
-- Ilk basta DEFAULT vermiyoruz; cunku eski magazalari
-- onaylanmis olarak korumak istiyoruz.
ALTER TABLE sellers
ADD COLUMN IF NOT EXISTS approval_status VARCHAR(20);

-- Daha once acilmis magazalari onaylanmis kabul et.
UPDATE sellers
SET approval_status = 'approved'
WHERE approval_status IS NULL;

-- Onceki kodla acilip beklemede kalmis magazalarin sahipleri
-- admin onayindan once satici yetkisi tasimamalidir.
UPDATE users AS u
SET role = 'customer'
FROM sellers AS s
WHERE s.owner_user_id = u.id
  AND s.approval_status = 'pending'
  AND u.role = 'seller';

-- Bundan sonra acilacak magazalar onay bekleyecek.
ALTER TABLE sellers
ALTER COLUMN approval_status SET DEFAULT 'pending';

ALTER TABLE sellers
ALTER COLUMN approval_status SET NOT NULL;

-- Basvuruyu inceleyen yonetici ve inceleme bilgileri.
ALTER TABLE sellers
ADD COLUMN IF NOT EXISTS reviewed_by BIGINT
    REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE sellers
ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ;

ALTER TABLE sellers
ADD COLUMN IF NOT EXISTS review_reason TEXT;

-- Admin tarafindan belirlenecek komisyon orani.
-- Simdilik NULL; henuz varsayilan yuzde secmiyoruz.
ALTER TABLE sellers
ADD COLUMN IF NOT EXISTS commission_rate_percent NUMERIC(5, 2);

-- Gecerli basvuru durumlari.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'sellers'::regclass
          AND conname = 'sellers_approval_status_check'
    ) THEN
        ALTER TABLE sellers
        ADD CONSTRAINT sellers_approval_status_check
        CHECK (
            approval_status IN (
                'pending',
                'approved',
                'rejected'
            )
        );
    END IF;
END
$$;

-- Komisyon orani 0 ile 100 arasinda olmali.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'sellers'::regclass
          AND conname = 'sellers_commission_rate_check'
    ) THEN
        ALTER TABLE sellers
        ADD CONSTRAINT sellers_commission_rate_check
        CHECK (
            commission_rate_percent IS NULL
            OR (
                commission_rate_percent >= 0
                AND commission_rate_percent <= 100
            )
        );
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_sellers_approval_status
ON sellers(approval_status);


-- ==========================================
-- 2. ADMIN ISLEM KAYITLARI
-- ==========================================

CREATE TABLE IF NOT EXISTS admin_audit_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    -- Islemi yapan admin.
    actor_user_id BIGINT NOT NULL
        REFERENCES users(id),

    -- Ornek: seller.approved, seller.rejected
    action VARCHAR(80) NOT NULL,

    -- Ornek: seller, order, product
    target_type VARCHAR(40) NOT NULL,

    target_id BIGINT NOT NULL,

    -- Islem oncesi ve sonrasi durum.
    before_data JSONB,
    after_data JSONB,

    reason TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_admin_audit_logs_target
ON admin_audit_logs(target_type, target_id);

CREATE INDEX IF NOT EXISTS idx_admin_audit_logs_created_at
ON admin_audit_logs(created_at DESC);

COMMIT;
