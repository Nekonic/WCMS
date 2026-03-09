import { describe, it, expect } from 'vitest'
import { Hono } from 'hono'
import { createPcsRouter } from '../routes/pcs.js'
import { createAdminRouter } from '../routes/admin.js'
import { createTestDb, insertPc } from './setup.js'

function makeApp() {
  const { db } = createTestDb()
  const app = new Hono()
  app.route('/admin', createAdminRouter(db))
  app.route('/pcs', createPcsRouter(db))
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

describe('GET /pcs/public', () => {
  it('returns list of verified PCs without auth', async () => {
    const { app, db } = makeApp()
    insertPc(db, 'public-machine')

    const res = await app.request('/pcs/public')
    expect(res.status).toBe(200)
    const body = await res.json() as any[]
    expect(body.length).toBe(1)
    expect(body[0].hostname).toBe('TEST-PC')
  })
})

describe('GET /pcs', () => {
  it('returns full PC list for admin', async () => {
    const { app, db } = makeApp()
    insertPc(db)
    const cookie = await loginCookie(app)

    const res = await app.request('/pcs', { headers: { cookie } })
    expect(res.status).toBe(200)
    const body = await res.json() as any[]
    expect(body.length).toBe(1)
  })

  it('returns 401 without auth', async () => {
    const { app } = makeApp()
    const res = await app.request('/pcs')
    expect(res.status).toBe(401)
  })
})

describe('GET /pcs/:id', () => {
  it('returns PC details', async () => {
    const { app, db } = makeApp()
    const pcId = insertPc(db)
    const cookie = await loginCookie(app)

    const res = await app.request(`/pcs/${pcId}`, { headers: { cookie } })
    expect(res.status).toBe(200)
    const body = await res.json() as any
    expect(body.id).toBe(pcId)
  })

  it('returns 404 for unknown id', async () => {
    const { app } = makeApp()
    const cookie = await loginCookie(app)
    const res = await app.request('/pcs/9999', { headers: { cookie } })
    expect(res.status).toBe(404)
  })
})

describe('DELETE /pcs/:id', () => {
  it('deletes a PC', async () => {
    const { app, db } = makeApp()
    const pcId = insertPc(db)
    const cookie = await loginCookie(app)

    const delRes = await app.request(`/pcs/${pcId}`, {
      method: 'DELETE',
      headers: { cookie },
    })
    expect(delRes.status).toBe(200)

    const getRes = await app.request(`/pcs/${pcId}`, { headers: { cookie } })
    expect(getRes.status).toBe(404)
  })
})

describe('POST /pcs/:id/command', () => {
  it('enqueues a command', async () => {
    const { app, db } = makeApp()
    const pcId = insertPc(db)
    const cookie = await loginCookie(app)

    const res = await app.request(`/pcs/${pcId}/command`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', cookie },
      body: JSON.stringify({ command_type: 'shutdown' }),
    })
    expect(res.status).toBe(200)
    const body = await res.json() as any
    expect(body.status).toBe('ok')
    expect(typeof body.command_id).toBe('number')
  })

  it('returns 404 for unknown PC', async () => {
    const { app } = makeApp()
    const cookie = await loginCookie(app)
    const res = await app.request('/pcs/9999/command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', cookie },
      body: JSON.stringify({ command_type: 'shutdown' }),
    })
    expect(res.status).toBe(404)
  })
})

describe('POST /pcs/:id/shutdown', () => {
  it('enqueues shutdown command', async () => {
    const { app, db } = makeApp()
    const pcId = insertPc(db)
    const cookie = await loginCookie(app)

    const res = await app.request(`/pcs/${pcId}/shutdown`, {
      method: 'POST',
      headers: { cookie },
    })
    expect(res.status).toBe(200)
  })
})