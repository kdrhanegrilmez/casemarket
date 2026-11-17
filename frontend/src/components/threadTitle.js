export function threadTitle(thread, audience) {
  if (thread.kind === 'product_moderation') return `Ürün #${thread.product_id} · Yayın incelemesi`
  if (thread.kind === 'product_question') return `Ürün #${thread.product_id} · ${thread.product_name || 'Ürün sorusu'}`
  if (audience === 'admin') return thread.customer_name || thread.seller_name || 'Destek talebi'
  return thread.kind === 'customer_support' ? 'Müşteri desteği' : 'Satıcı desteği'
}
