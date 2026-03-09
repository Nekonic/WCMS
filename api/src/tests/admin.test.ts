import { describe, it, expect, beforeEach } from 'vitest'
import { Hono } from 'hono'
import { createAdminRouter } from '../routes/admin.js'
import { createTestDb, insertToken } from './setup.js'

function makeApp() {
  const { db } = createTestDb()
  const app = new Hono()
  app.route('/admin', createAdminRouter(db))
  return { app, db }
}

async function loginCookie(app: Hono) {
  const res = await app.request('/admin/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'admin', password: 'password123' }),
  })
  return res.headers.get('set-cookie') ?? ''
}

describe('POST /admin/login', () => {
  it('returns ok with valid credentials', async () => {
    const { app } = makeApp()
    const res = await app.request('/admin/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: 'admin', password: 'password123' }),
    })
    expect(res.status).toBe(200)
    const body = await res.json() as any
    expect(body.status).toBe('ok')
    expect(body.username).toBe('admin')
  })

  it('returns 401 with wrong password', async () => {
    const { app } = makeApp()
    const res = await app.request('/admin/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: 'admin', password: 'wrong' }),
    })
    expect(res.status).toBe(401)
  })

  it('returns 401 with unknown username', async () => {
    const { app } = makeApp()
    const res = await app.request('/admin/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: 'nobody', password: 'password123' }),
    })
    expect(res.status).toBe(401)
  })
})

describe('GET /admin/me', () => {
  it('returns username when logged in', async () => {
    const { app } = makeApp()
    const cookie = await loginCookie(app)
    const res = await app.request('/admin/me', {
      headers: { cookie },
    })
    expect(res.status).toBe(200)
    const body = await res.json() as any
    expect(body.username).toBe('admin')
  })

  it('returns 401 without session', async () => {
    const { app } = makeApp()
    const res = await app.request('/admin/me')
    expect(res.status).toBe(401)
  })
})

describe('POST /admin/logout', () => {
  it('clears session cookie', async () => {
    const { app } = makeApp()
    const res = await app.request('/admin/logout', { method: 'POST' })
    expect(res.status).toBe(200)
  })
})

describe('GET /admin/tokens', () => {
  it('returns token list when logged in', async () => {
    const { app, db } = makeApp()
    insertToken(db, { token: '111111' })
    const cookie = await loginCookie(app)
    const res = await app.request('/admin/tokens', { headers: { cookie } })
    expect(res.status).toBe(200)
    const body = await res.json() as any[]
    expect(body.length).toBe(1)
    expect(body[0].token).toBe('111111')
  })

  it('returns 401 without session', async () => {
    const { app } = makeApp()
    const res = await app.request('/admin/tokens')
    expect(res.status).toBe(401)
  })
})

describe('POST /admin/tokens', () => {
  it('creates a new token', async () => {
    const { app } = makeApp()
    const cookie = await loginCookie(app)
    const res = await app.request('/admin/tokens', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', cookie },
      body: JSON.stringify({ usage_type: 'single', expires_in: 600 }),
    })
    expect(res.status).toBe(201)
    const body = await res.json() as any
    expect(body.status).toBe('ok')
    expect(body.pin).toMatch(/^\d{6}$/)
  })
})

describe('DELETE /admin/tokens/:id', () => {
  it('marks token as expired', async () => {
    const { app, db } = makeApp()
    insertToken(db, { token: '222222' })
    const cookie = await loginCookie(app)

    // Get token id
    const listRes = await app.request('/admin/tokens', { headers: { cookie } })
    const tokens = await listRes.json() as any[]
    const id = tokens[0].id

    const res = await app.request(`/admin/tokens/${id}`, {
      method: 'DELETE',
      headers: { cookie },
    })
    expect(res.status).toBe(200)
  })
})