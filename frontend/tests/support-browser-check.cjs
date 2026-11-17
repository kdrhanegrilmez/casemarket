const { chromium } = require('playwright')
const assert = require('node:assert/strict')
require('node:fs').mkdirSync('/tmp/casemarket-support-check', { recursive: true })

async function scenario(browser, role, channel = 'support') {
  const page = await browser.newPage({ viewport: { width: 1180, height: 900 } })
  await page.clock.install()
  const requests = []
  const errors = []
  page.on('pageerror', error => errors.push(error.message))
  const kind = channel === 'questions' ? 'product_question' : `${role}_support`
  const threads = [{ id: 1, kind, product_id: channel === 'questions' ? 50 : null,
    product_name: 'Test Kılıf', store_name: 'Test Mağazası', status: channel === 'questions' ? 'open' : 'closed',
    customer_name: 'Müşteri', seller_name: 'Satıcı', unread_count: 0, last_message: 'Eski talep',
    messages: [{ id: 1, sender_user_id: 2, sender_role: 'admin', sender_name: 'Admin', body: 'Eski talep', created_at: new Date().toISOString() }] }]
  await page.route('**/api/support/**', async route => {
    const url = new URL(route.request().url())
    const path = url.pathname.replace('/api/support', '')
    const method = route.request().method()
    requests.push(`${method} ${path}`)
    let body = {}
    let status = 200
    if (path.endsWith('/unread-count')) body = { unread_count: 0 }
    else if (path === '/my/threads' || path === '/admin/threads') {
      const state = url.searchParams.get('status')
      body = threads.filter(t => state === 'all' || t.status === state).map(({messages, ...t}) => t)
    } else if (method === 'POST' && (path === '/customer' || path === '/seller' || path.includes('/question'))) {
      let thread = threads.find(t => t.status === 'open')
      if (!thread) { thread = { ...threads[0], id: threads.length + 1, status: 'open', messages: [] }; threads.push(thread) }
      const message = route.request().postDataJSON().message
      thread.messages.push({ id: Date.now(), sender_user_id: role === 'seller' ? 9 : 7, sender_role: role, sender_name: role, body: message, created_at: new Date().toISOString() })
      body = { thread_id: thread.id }; status = 201
    } else if (/^\/threads\/\d+\/status$/.test(path)) {
      const t = threads.find(t => t.id === Number(path.split('/')[2]))
      t.status = route.request().postDataJSON().status
      t.closed_at = new Date().toISOString()
      body = { thread_id: t.id, status: t.status, closed_at: t.closed_at }
    } else if (/^\/threads\/\d+\/messages$/.test(path)) {
      const t = threads.find(t => t.id === Number(path.split('/')[2]))
      t.messages.push({ id: Date.now(), body: route.request().postDataJSON().message, sender_user_id: 7, sender_role: role, sender_name: role, created_at: new Date().toISOString() })
      body = { id: t.messages.at(-1).id }; status = 201
    } else if (/^\/threads\/\d+$/.test(path)) {
      const t = threads.find(t => t.id === Number(path.split('/')[2]))
      const { messages, ...thread } = t
      body = { thread, messages }
    } else throw new Error(`Unexpected request ${method} ${path}`)
    await route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body), headers: { 'Access-Control-Allow-Origin': '*' } })
  })
  await page.goto(`http://localhost:5173/tests/support-browser-check.html?role=${role}&channel=${channel}`)
  const composer = page.getByRole('textbox', { name: 'Mesaj', exact: true })
  if (channel === 'questions') {
    await page.getByRole('button', { name: 'Görüşmeyi sonlandır', exact: true }).click()
    await page.getByText('Bu görüşme sonlandırıldı.', { exact: false }).waitFor()
    assert.equal(await composer.count(), 0)
    if (role === 'customer') await page.getByRole('button', { name: 'Yeni soru sor', exact: true }).click()
  }
  if (channel === 'support' || role === 'customer') {
    await composer.fill('Yeni talebimi açıyorum')
    await page.getByRole('button', { name: 'Gönder ↗', exact: true }).click()
    await page.getByText('Yeni talebimi açıyorum', { exact: true }).last().waitFor()
    assert.equal(threads.length, 2)
    assert.equal(threads[0].status, 'closed')
    await page.waitForTimeout(100)
    const before = requests.filter(x => x === 'GET /threads/2').length
    for (let step = 0; step < 3; step++) {
      await page.clock.runFor(8500)
      await page.waitForTimeout(50)
    }
    const activePolls = requests.filter(x => x === 'GET /threads/2').length - before
    assert.ok(activePolls >= 1 && activePolls <= 4, `Unexpected active polling burst: ${activePolls}`)
    if (role === 'customer' && channel === 'support') {
      threads[1].status = 'closed'
      await page.clock.runFor(8500)
      await page.waitForTimeout(100)
      if (await page.getByText('Bu görüşme sonlandırıldı.', { exact: false }).count()) {
        assert.equal(await page.getByRole('button', { name: 'Sonlandırılan', exact: true }).getAttribute('aria-pressed'), 'true')
      } else await composer.waitFor()
      await page.getByRole('button', { name: 'Devam eden', exact: true }).click()
      await composer.waitFor()
      assert.equal(await page.getByText('Bu görüşme sonlandırıldı.', { exact: false }).count(), 0)
    }
  }

  // Geçmişteki bitmiş görüşmeyi seçince detay ve liste için periyodik istek yapılmamalı.
  await page.getByRole('button', { name: 'Sonlandırılan', exact: true }).click()
  await page.getByText('Bu görüşme sonlandırıldı.', { exact: false }).waitFor()
  const detailBefore = requests.filter(x => x === 'GET /threads/1').length
  const listBefore = requests.filter(x => x === 'GET /my/threads').length
  await page.clock.runFor(32000)
  assert.equal(requests.filter(x => x === 'GET /threads/1').length, detailBefore, 'Closed conversation kept polling')
  assert.equal(requests.filter(x => x === 'GET /my/threads').length, listBefore, 'Closed list kept polling')

  await page.evaluate(() => {
    window.testHidden = true
    Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => window.testHidden ? 'hidden' : 'visible' })
    document.dispatchEvent(new Event('visibilitychange'))
  })
  const hiddenBefore = requests.length
  await page.clock.runFor(32000)
  assert.equal(requests.length, hiddenBefore, 'Hidden tab sent polling requests')
  await page.evaluate(() => { window.testHidden = false; document.dispatchEvent(new Event('visibilitychange')) })
  await page.clock.runFor(100)
  assert.ok(requests.length > hiddenBefore, 'Visible tab did not refresh')
  assert.deepEqual(errors, [])
  if (role === 'customer') {
    await page.setViewportSize({ width: 390, height: 844 })
    const box = await page.locator('.customer-support-widget__panel').boundingBox()
    assert.equal(box.x, 0)
    assert.ok(box.width <= 390, `Mobile panel overflows: ${box.width}`)
  }
  await page.screenshot({ path: `/tmp/casemarket-support-check/${role}-${channel}.png` })
  console.log(`${role}/${channel}: new session, completion, closed polling and hidden polling OK`)
  await page.close()
}

;(async () => {
  const browser = await chromium.launch({ headless: true })
  try {
    await scenario(browser, 'customer')
    await scenario(browser, 'seller')
    await scenario(browser, 'customer', 'questions')
    await scenario(browser, 'seller', 'questions')
  } finally { await browser.close() }
})().catch(error => { console.error(error); process.exit(1) })
