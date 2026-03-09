import { Hono } from 'hono'
import { zValidator } from '@hono/zod-validator'
import { z } from 'zod'
import { eq, desc, and, gte } from 'drizzle-orm'
import { compareSync } from 'bcryptjs'
import { randomInt } from 'crypto'
import type { DB } from '../db/index.js'
import { admins, pcRegistrationTokens, pcDynamicInfo, pcInfo } from '../db/schema.js'
import { requireAdmin, setSession, clearSession } from '../middleware/auth.js'

const LoginSchema = z.object({
  username: z.string().min(1),
  password: z.string().min(1),
})

const TokenSchema = z.object({
  usage_type: z.enum(['single', 'multi']).default('single'),
  expires_in: z.number().int().min(60).max(86400).default(600),
})

export function createAdminRouter(db: DB) {
  const router = new Hono()

  // ==================== 인증 ====================

  router.post('/login', zValidator('json', LoginSchema), async (c) => {
    const { username, password } = c.req.valid('json')

    const admin = db.select().from(admins)
      .where(and(eq(admins.username, username), eq(admins.isActive, true)))
      .get()

    if (!admin || !compareSync(password, admin.passwordHash)) {
      return c.json({ status: 'error', message: 'Invalid credentials' }, 401)
    }

    db.update(admins).set({ lastLogin: new Date().toISOString() })
      .where(eq(admins.id, admin.id)).run()

    setSession(c, { adminId: admin.id, username: admin.username })
    return c.json({ status: 'ok', username: admin.username })
  })

  router.post('/logout', (c) => {
    clearSession(c)
    return c.json({ status: 'ok' })
  })

  router.get('/me', requireAdmin, (c) => {
    const session = c.get('session')
    return c.json({ username: session.username })
  })

  // ==================== 등록 토큰 ====================

  router.get('/tokens', requireAdmin, async (c) => {
    const tokens = db.select().from(pcRegistrationTokens)
      .orderBy(desc(pcRegistrationTokens.createdAt))
      .all()
    return c.json(tokens)
  })

  router.post('/tokens', requireAdmin, zValidator('json', TokenSchema), async (c) => {
    const session = c.get('session')
    const { usage_type, expires_in } = c.req.valid('json')

    const pin = String(randomInt(100000, 999999))
    const expiresAt = new Date(Date.now() + expires_in * 1000).toISOString()

    db.insert(pcRegistrationTokens).values({
      token:      pin,
      usageType:  usage_type,
      expiresIn:  expires_in,
      createdBy:  session.username,
      expiresAt,
    }).run()

    return c.json({ status: 'ok', pin, expires_at: expiresAt }, 201)
  })

  router.delete('/tokens/:id', requireAdmin, async (c) => {
    const id = Number(c.req.param('id'))
    db.update(pcRegistrationTokens).set({ isExpired: true })
      .where(eq(pcRegistrationTokens.id, id)).run()
    return c.json({ status: 'ok' })
  })

  // ==================== 프로세스 목록 ====================

  router.get('/processes', requireAdmin, async (c) => {
    const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000).toISOString()

    const rows = db.select({
      pcId:        pcInfo.id,
      hostname:    pcInfo.hostname,
      processes:   pcDynamicInfo.processes,
      updatedAt:   pcDynamicInfo.updatedAt,
    })
      .from(pcDynamicInfo)
      .innerJoin(pcInfo, eq(pcDynamicInfo.pcId, pcInfo.id))
      .where(gte(pcDynamicInfo.updatedAt, oneHourAgo))
      .all()

    return c.json(rows.map(r => ({
      pc_id:     r.pcId,
      hostname:  r.hostname,
      processes: r.processes ? JSON.parse(r.processes) : [],
      updated_at: r.updatedAt,
    })))
  })

  return router
}