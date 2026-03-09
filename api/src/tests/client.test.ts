import { describe, it, expect } from 'vitest'
import { Hono } from 'hono'
import { createClientRouter } from '../routes/client.js'
import { createTestDb, insertToken, insertPc } from './setup.js'

function makeApp() {
  const { db } = createTestDb()
  const app = new Hono()
  app.route('/client', createClientRouter(db))
  return { app, db }
}

describe('POST /client/register', () => {
  it('registers a new PC with valid token', async () => {
    const { app, db } = makeApp()
    insertToken(db, { token: '123456' })

    const res = await app.request('/client/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        machine_id:  'test-machine-001',
        pin:         '123456',
        hostname:    'TEST-PC',
        mac_address: 'AA:BB:CC:DD:EE:FF',
      }),
    })
    expect(res.status).toBe(200)
    const body = await res.json() as any
    expect(body.status).toBe('success')
    expect(typeof body.pc_id).toBe('number')
  })

  it('rejects invalid PIN', async () => {
    const { app } = makeApp()
    const res = await app.request('/client/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ machine_id: 'test-001', pin: '999999' }),
    })
    expect(res.status).toBe(403)
    const body = await res.json() as any
    expect(body.message).toBe('Invalid PIN')
  })

  it('rejects expired token', async () => {
    const { app, db } = makeApp()
    insertToken(db, { token: '123456', expired: true })

    const res = await app.request('/client/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ machine_id: 'test-001', pin: '123456' }),
    })
    expect(res.status).toBe(403)
    const body = await res.json() as any
    expect(body.message).toBe('PIN expired')
  })

  it('rejects second use of single-use token', async () => {
    const { app, db } = makeApp()
    insertToken(db, { token: '123456', usageType: 'single' })

    // First use
    await app.request('/client/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ machine_id: 'machine-A', pin: '123456' }),
    })

    // Second use
    const res = await app.request('/client/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ machine_id: 'machine-B', pin: '123456' }),
    })
    expect(res.status).toBe(403)
    const body = await res.json() as any
    expect(body.message).toBe('PIN already used (single-use token)')
  })

  it('allows multi-use token to be used multiple times', async () => {
    const { app, db } = makeApp()
    insertToken(db, { token: '123456', usageType: 'multi' })

    for (const machineId of ['machine-A', 'machine-B']) {
      const res = await app.request('/client/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ machine_id: machineId, pin: '123456', hostname: machineId }),
      })
      expect(res.status).toBe(200)
    }
  })
})

describe('POST /client/heartbeat', () => {
  it('returns ok for registered PC', async () => {
    const { app, db } = makeApp()
    insertPc(db, 'hb-machine')

    const res = await app.request('/client/heartbeat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        machine_id:        'hb-machine',
        cpu_usage:         10.5,
        ram_used:          4.0,
        ram_usage_percent: 50.0,
        uptime:            3600,
      }),
    })
    expect(res.status).toBe(200)
    const body = await res.json() as any
    expect(body.status).toBe('ok')
  })

  it('returns 404 for unknown machine', async () => {
    const { app } = makeApp()
    const res = await app.request('/client/heartbeat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        machine_id:        'ghost-machine',
        cpu_usage:         0,
        ram_used:          0,
        ram_usage_percent: 0,
        uptime:            0,
      }),
    })
    expect(res.status).toBe(404)
  })
})

describe('POST /client/offline', () => {
  it('returns ok for registered PC', async () => {
    const { app, db } = makeApp()
    insertPc(db, 'offline-machine')

    const res = await app.request('/client/offline', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ machine_id: 'offline-machine', reason: 'shutdown' }),
    })
    expect(res.status).toBe(200)
  })

  it('returns ok for unknown machine (graceful)', async () => {
    const { app } = makeApp()
    const res = await app.request('/client/offline', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ machine_id: 'ghost', reason: 'unknown' }),
    })
    expect(res.status).toBe(200)
  })
})

describe('GET /client/version', () => {
  it('returns null when no version exists', async () => {
    const { app } = makeApp()
    const res = await app.request('/client/version')
    expect(res.status).toBe(200)
    const body = await res.json() as any
    expect(body.version).toBeNull()
  })
})

describe('GET /client/commands', () => {
  it('returns error without machine_id', async () => {
    const { app } = makeApp()
    // Use timeout=0 to avoid actual waiting
    const res = await app.request('/client/commands?timeout=0')
    expect(res.status).toBe(400)
  })

  it('returns 404 for unknown machine', async () => {
    const { app } = makeApp()
    const res = await app.request('/client/commands?machine_id=ghost&timeout=0')
    expect(res.status).toBe(404)
  })

  it('returns no_command when queue is empty', async () => {
    const { app, db } = makeApp()
    insertPc(db, 'cmd-machine')

    const res = await app.request('/client/commands?machine_id=cmd-machine&timeout=0')
    expect(res.status).toBe(200)
    const body = await res.json() as any
    expect(body.status).toBe('no_command')
  })
})