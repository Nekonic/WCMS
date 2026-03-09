import { Hono } from 'hono'
import { zValidator } from '@hono/zod-validator'
import { z } from 'zod'
import { eq, and, desc, sql, ne } from 'drizzle-orm'
import type { DB } from '../db/index.js'
import { pcInfo, pcSpecs, pcDynamicInfo, commands, networkEvents } from '../db/schema.js'
import { requireAdmin } from '../middleware/auth.js'

const OFFLINE_THRESHOLD_SEC = 40

export function createPcsRouter(db: DB) {
  const router = new Hono()

  // 오프라인 판정 (마지막 heartbeat 기준)
  function markOfflineIfStale() {
    const threshold = new Date(Date.now() - OFFLINE_THRESHOLD_SEC * 1000).toISOString()
    db.update(pcInfo).set({ isOnline: false })
      .where(and(eq(pcInfo.isOnline, true), sql`last_seen < ${threshold}`))
      .run()
  }

  // ==================== PC 조회 ====================

  // 공개 정보 (인증 불필요 — Svelte 메인 화면)
  router.get('/public', async (c) => {
    markOfflineIfStale()
    const pcs = db.select({
      id:       pcInfo.id,
      hostname: pcInfo.hostname,
      roomName: pcInfo.roomName,
      seatNumber: pcInfo.seatNumber,
      isOnline: pcInfo.isOnline,
      lastSeen: pcInfo.lastSeen,
    }).from(pcInfo).where(eq(pcInfo.isVerified, true)).all()
    return c.json(pcs)
  })

  // 전체 목록 (관리자)
  router.get('/', requireAdmin, async (c) => {
    markOfflineIfStale()
    const roomFilter = c.req.query('room')

    const rows = db.select({
      pc:   pcInfo,
      spec: pcSpecs,
      dyn:  pcDynamicInfo,
    })
      .from(pcInfo)
      .leftJoin(pcSpecs, eq(pcSpecs.pcId, pcInfo.id))
      .leftJoin(pcDynamicInfo, eq(pcDynamicInfo.pcId, pcInfo.id))
      .where(roomFilter ? eq(pcInfo.roomName, roomFilter) : undefined)
      .all()

    return c.json(rows.map(r => ({
      ...r.pc,
      spec: r.spec,
      dynamic: r.dyn,
    })))
  })

  // 중복 호스트명
  router.get('/duplicates', requireAdmin, async (c) => {
    const dupes = db.all(sql`
      SELECT hostname, COUNT(*) as count, GROUP_CONCAT(id) as ids
      FROM pc_info GROUP BY hostname HAVING count > 1
    `)
    return c.json(dupes)
  })

  // 미검증 PC
  router.get('/unverified', requireAdmin, async (c) => {
    const pcs = db.select().from(pcInfo).where(eq(pcInfo.isVerified, false)).all()
    return c.json(pcs)
  })

  // PC 상세
  router.get('/:id', requireAdmin, async (c) => {
    markOfflineIfStale()
    const id = Number(c.req.param('id'))

    const row = db.select({ pc: pcInfo, spec: pcSpecs, dyn: pcDynamicInfo })
      .from(pcInfo)
      .leftJoin(pcSpecs, eq(pcSpecs.pcId, pcInfo.id))
      .leftJoin(pcDynamicInfo, eq(pcDynamicInfo.pcId, pcInfo.id))
      .where(eq(pcInfo.id, id))
      .get()

    if (!row) return c.json({ error: 'PC not found' }, 404)
    return c.json({ ...row.pc, spec: row.spec, dynamic: row.dyn })
  })

  // PC 프로세스 기록
  router.get('/:id/history', requireAdmin, async (c) => {
    const pcId = Number(c.req.param('id'))
    const events = db.select().from(networkEvents)
      .where(eq(networkEvents.pcId, pcId))
      .orderBy(desc(networkEvents.offlineAt))
      .limit(100)
      .all()
    return c.json(events)
  })

  // PC 삭제
  router.delete('/:id', requireAdmin, async (c) => {
    const id = Number(c.req.param('id'))
    db.delete(pcInfo).where(eq(pcInfo.id, id)).run()
    return c.json({ status: 'ok' })
  })

  // ==================== PC 명령 ====================

  const CommandSchema = z.object({
    command_type: z.string(),
    command_data: z.record(z.unknown()).optional(),
    priority:     z.number().int().min(1).max(10).optional().default(5),
    timeout:      z.number().int().optional().default(300),
  })

  function sendCommand(pcId: number, adminUsername: string, cmd: z.infer<typeof CommandSchema>) {
    return db.insert(commands).values({
      pcId,
      adminUsername,
      commandType:    cmd.command_type,
      commandData:    cmd.command_data ? JSON.stringify(cmd.command_data) : null,
      priority:       cmd.priority,
      timeoutSeconds: cmd.timeout,
    }).returning({ id: commands.id }).get()
  }

  // 범용 명령
  router.post('/:id/command', requireAdmin, zValidator('json', CommandSchema), async (c) => {
    const pcId = Number(c.req.param('id'))
    const session = c.get('session')
    const cmd = c.req.valid('json')

    const pc = db.select({ id: pcInfo.id }).from(pcInfo).where(eq(pcInfo.id, pcId)).get()
    if (!pc) return c.json({ error: 'PC not found' }, 404)

    const result = sendCommand(pcId, session.username, cmd)
    return c.json({ status: 'ok', command_id: result.id })
  })

  // 단축 명령 팩토리
  function quickCommand(commandType: string, schema?: z.ZodTypeAny) {
    return [
      requireAdmin,
      async (c: any) => {
        const pcId = Number(c.req.param('id'))
        const session = c.get('session')

        let body: Record<string, unknown> = {}
        if (schema) {
          const raw = await c.req.json().catch(() => ({}))
          const parsed = schema.safeParse(raw)
          if (!parsed.success) return c.json({ error: parsed.error.flatten() }, 400)
          body = parsed.data
        }

        const pc = db.select({ id: pcInfo.id }).from(pcInfo).where(eq(pcInfo.id, pcId)).get()
        if (!pc) return c.json({ error: 'PC not found' }, 404)

        const result = sendCommand(pcId, session.username, {
          command_type: commandType,
          command_data: body,
          priority: 5,
          timeout: 300,
        })
        return c.json({ status: 'ok', command_id: result.id })
      },
    ] as const
  }

  router.post('/:id/shutdown',         ...quickCommand('shutdown'))
  router.post('/:id/restart',          ...quickCommand('restart'))   // reboot 통합
  router.post('/:id/message',          ...quickCommand('show_message', z.object({ message: z.string(), duration: z.number().optional() })))
  router.post('/:id/kill-process',     ...quickCommand('kill_process', z.object({ process_name: z.string() })))
  router.post('/:id/install',          ...quickCommand('install', z.object({ package_name: z.string() })))
  router.post('/:id/uninstall',        ...quickCommand('uninstall', z.object({ package_name: z.string() })))
  router.post('/:id/account/create',   ...quickCommand('create_user', z.object({ username: z.string(), password: z.string(), language: z.string().optional() })))
  router.post('/:id/account/delete',   ...quickCommand('delete_user', z.object({ username: z.string() })))
  router.post('/:id/account/password', ...quickCommand('change_password', z.object({ username: z.string(), new_password: z.string() })))

  // 명령 큐 삭제
  router.delete('/:id/commands', requireAdmin, async (c) => {
    const pcId = Number(c.req.param('id'))
    db.delete(commands)
      .where(and(eq(commands.pcId, pcId), eq(commands.status, 'pending')))
      .run()
    return c.json({ status: 'ok' })
  })

  return router
}