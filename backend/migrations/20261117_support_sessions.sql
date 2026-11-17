-- Sonlandırılmış geçmiş korunur; aynı kapsamda yalnızca bir açık görüşme bulunabilir.
DROP INDEX IF EXISTS idx_support_customer_thread;
DROP INDEX IF EXISTS idx_support_seller_thread;
DROP INDEX IF EXISTS idx_support_question_thread;

CREATE UNIQUE INDEX idx_support_customer_thread
ON support_threads(customer_user_id) WHERE kind = 'customer_support' AND status = 'open';
CREATE UNIQUE INDEX idx_support_seller_thread
ON support_threads(seller_user_id) WHERE kind = 'seller_support' AND status = 'open';
CREATE UNIQUE INDEX idx_support_question_thread
ON support_threads(customer_user_id, product_id) WHERE kind = 'product_question' AND status = 'open';
