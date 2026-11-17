const { chromium } = require('playwright')
const assert = require('node:assert/strict')
const fs = require('node:fs')
fs.mkdirSync('/tmp/casemarket-support-check', { recursive: true })

;(async () => {
  const browser = await chromium.launch({ headless: true })
  try {
    const page = await browser.newPage({ viewport: { width: 1292, height: 900 } })
    const errors = []
    page.on('pageerror', error => errors.push(error.message))
    await page.route('**/api/**', async route => {
      const path = new URL(route.request().url()).pathname
      if (!path.startsWith('/api/')) return route.continue()
      let body
      if (path === '/api/admin/stores') body = { items: [1, 2, 3, 4].map(id => ({ id,
        store_name: id === 2 ? 'CaseMarket 2. Deneme Mağazası' : `Test Kılıf Mağazası ${id}`,
        owner_name: 'Test Satıcı', owner_email: 'uzun.magaza.sahibi@example.com',
        approval_status: 'approved', product_count: 5, commission_rate_percent: '35.00', is_temporarily_closed: false,
      })), has_more: false }
      else if (path === '/api/admin/overview') body = { paid_orders: 0, gross_sales: 0, sellers: 4, products: 20, pending_stores: 0, approved_stores: 4, daily_orders: [], recent_orders: [] }
      else if (path === '/api/support/admin/unread-count' || path === '/api/support/my/unread-count') body = { unread_count: 0 }
      else if (path === '/api/sellers/me') body = { id: 3, store_name: 'Test Kılıf Mağazası', description: 'Test' }
      else if (path === '/api/sellers/me/products' || path === '/api/sellers/me/orders' || path === '/api/support/my/threads') body = []
      else if (path === '/api/catalog/filters') body = { brands: [], categories: [] }
      else throw new Error(`Unexpected request: ${path}`)
      await route.fulfill({ contentType: 'application/json', body: JSON.stringify(body), headers: { 'Access-Control-Allow-Origin': '*' } })
    })
    await page.goto('http://localhost:5173/tests/support-browser-check.html?role=admin-stores')
    await page.getByRole('button', { name: 'Mağazalar', exact: true }).click()
    const table = page.locator('.admin-stores')
    await table.getByRole('button', { name: 'Geçici kapat', exact: true }).first().waitFor()
    async function fits() {
      const size = await table.evaluate(el => ({ scroll: el.scrollWidth, client: el.clientWidth }))
      assert.ok(size.scroll <= size.client + 1, `Store table overflows: ${JSON.stringify(size)}`)
    }
    await fits()
    const before = await table.boundingBox()
    await table.getByRole('button', { name: 'Geçici kapat', exact: true }).first().click()
    const dialog = page.getByRole('dialog')
    await dialog.waitFor()
    await dialog.getByRole('textbox', { name: 'Geçici kapatma gerekçesi' }).fill('Geçici inceleme')
    await fits()
    assert.equal((await table.boundingBox()).height, before.height, 'Opening closure form expanded table row')
    const d = await dialog.boundingBox()
    assert.ok(d.x >= 0 && d.x + d.width <= 1292)
    await page.screenshot({ path: '/tmp/casemarket-support-check/store-dialog.png' })
    await page.keyboard.press('Escape')
    await dialog.waitFor({ state: 'hidden' })
    await table.getByRole('button', { name: 'Yetkiyi geri al', exact: true }).first().click()
    await dialog.waitFor()
    await dialog.getByRole('textbox', { name: 'Yetki geri alma gerekçesi' }).fill('Denetim gerekçesi')
    await fits()
    await dialog.getByRole('button', { name: 'Vazgeç', exact: true }).click()
    for (const width of [1024, 390]) {
      await page.setViewportSize({ width, height: 900 })
      await fits()
      await table.getByRole('button', { name: 'Geçici kapat', exact: true }).first().click()
      const box = await dialog.boundingBox()
      assert.ok(box.x >= 0 && box.x + box.width <= width, `Dialog overflows at ${width}px`)
      await page.keyboard.press('Escape')
    }
    await page.setViewportSize({ width: 1292, height: 900 })
    await page.screenshot({ path: '/tmp/casemarket-support-check/stores-fit.png' })
    await page.goto('http://localhost:5173/tests/support-browser-check.html?role=seller-panel')
    await page.getByRole('tab', { name: 'Mesajlar', exact: true }).click()
    await page.locator('.thread-center__toolbar').waitFor()
    const primary = await page.locator('.seller-dashboard__tabs button').first().boundingBox()
    const secondary = await page.locator('.seller-communication__channels button').first().boundingBox()
    const tertiary = await page.locator('.thread-center__toolbar button').first().boundingBox()
    assert.ok(primary.height > secondary.height && secondary.height > tertiary.height,
      `Button hierarchy is wrong: ${primary.height}, ${secondary.height}, ${tertiary.height}`)
    assert.equal(await page.locator('.thread-center__toolbar button').count(), 3)
    assert.equal(await page.getByRole('button', { name: 'Yenile', exact: true }).count(), 0)
    await page.screenshot({ path: '/tmp/casemarket-support-check/seller-button-hierarchy.png' })
    assert.deepEqual(errors, [])
    console.log('Store table fits at 1292/1024/390px; dialogs stay in viewport; seller button hierarchy and removal of refresh verified.')
  } finally { await browser.close() }
})().catch(error => { console.error(error); process.exit(1) })
