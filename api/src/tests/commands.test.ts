import { describe, it, expect } from 'vitest'
import { Hono } from 'hono'
import { createCommandsRouter } from '../routes/commands.js'
import { createAdminRouter } from '../routes/admin.js'
import { createPcsRouter } from '../routes/pcs.js'
import { createTestDb, insertPc } from './setup.js'

function makeApp() {
  const { db } = createTestDb()
  const app = new Hono()
  app.route('/admin', createAdminRouter(db))
  app.route('/pcs', createPcsRouter(db))
  app.route('/commands', createCommandsRouter(db))
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

describe('GET /commands/pending', () => {
  it('returns empty list initially', async () => {
    const { app } = makeApp()
    const cookie = await loginCookie(app)
    const res = await app.request('/commands/pending', { headers: { cookie } })
    expect(res.status).toBe(200)
    const body = await res.json() as any[]
    expect(body).toEqual([])
  })

  it('returns 401 without auth', async () => {
    const { app } = makeApp()
    const res = await app.request('/commands/pending')
    expect(res.status).toBe(401)
  })
})

describe('POST /commands/bulk', () => {
  it('enqueues commands for multiple PCs', async () => {
    const { app, db } = makeApp()
    const pcId1 = insertPc(db, 'bulk-machine-1')
    const pcId2 = insertPc(db, 'bulk-machine-2')
    const cookie = await loginCookie(app)

    const res = await app.request('/commands/bulk', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', cookie },
      body: JSON.stringify({
        pc_ids: [pcId1, pcId2],
        command_type: 'shutdown',
      }),
    })
    expect(res.status).toBe(200)
    const body = await res.json() as any
    expect(body.status).toBe('ok')
    expect(body.command_ids).toHaveLength(2)
  })
})

describe('POST /commands/results', () => {
  it('returns command results', async () => {
    const { app, db } = makeApp()
    const pcId = insertPc(db)
    const cookie = await loginCookie(app)

    // Create a command first
    const cmdRes = await app.request(`/pcs/${pcId}/command`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', cookie },
      body: JSON.stringify({ command_type: 'shutdown' }),
    })
    const { command_id } = await cmdRes.json() as any

    const res = await app.request('/commands/results', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', cookie },
      body: JSON.stringify({ command_ids: [command_id] }),
    })
    expect(res.status).toBe(200)
    const body = await res.json() as any[]
    expect(body[0].id).toBe(command_id)
    expect(body[0].status).toBe('pending')
  })
})