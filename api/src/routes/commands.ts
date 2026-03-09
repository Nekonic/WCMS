import { Hono } from 'hono'
import { zValidator } from '@hono/zod-validator'
import { z } from 'zod'
import { eq, inArray, and, desc } from 'drizzle-orm'
import { db } from '../db/index.js'
import { commands, pcInfo } from '../db/schema.js'
import { requireAdmin } from '../middleware/auth.js'

export const commandsRouter = new Hono()

// 대기 명령 목록
commandsRouter.get('/pending', requireAdmin, async (c) => {
  const pending = db.select({
    id:          commands.id,
    pcId:        commands.pcId,
    hostname:    pcInfo.hostname,
    commandType: commands.commandType,
    priority:    commands.priority,
    createdAt:   commands.createdAt,
  })
    .from(commands)
    .innerJoin(pcInfo, eq(commands.pcId, pcInfo.id))
    .where(eq(commands.status, 'pending'))
    .orderBy(commands.priority, commands.createdAt)
    .all()

  return c.json(pending)
})

// 명령 결과 조회 (폴링 — Svelte 대시보드)
const ResultsQuerySchema = z.object({
  command_ids: z.array(z.number().int()).min(1),
})

commandsRouter.post('/results', requireAdmin, zValidator('json', ResultsQuerySchema), async (c) => {
  const { command_ids } = c.req.valid('json')
  const rows = db.select().from(commands)
    .where(inArray(commands.id, command_ids))
    .all()

  return c.json(rows.map(r => ({
    id:           r.id,
    status:       r.status,
    result:       r.result,
    error:        r.errorMessage,
    completed_at: r.completedAt,
  })))
})

// ==================== 일괄 명령 ====================

const BulkCommandSchema = z.object({
  pc_ids:       z.array(z.number().int()).min(1),
  command_type: z.string(),
  command_data: z.record(z.unknown()).optional(),
  priority:     z.number().int().min(1).max(10).optional().default(5),
  timeout:      z.number().int().optional().default(300),
})

commandsRouter.post('/bulk', requireAdmin, zValidator('json', BulkCommandSchema), async (c) => {
  const session = c.get('session')
  const data = c.req.valid('json')

  const commandIds: number[] = []
  for (const pcId of data.pc_ids) {
    const result = db.insert(commands).values({
      pcId,
      adminUsername:  session.username,
      commandType:    data.command_type,
      commandData:    data.command_data ? JSON.stringify(data.command_data) : null,
      priority:       data.priority,
      timeoutSeconds: data.timeout,
    }).returning({ id: commands.id }).get()
    commandIds.push(result.id)
  }

  return c.json({ status: 'ok', command_ids: commandIds })
})

// 여러 PC 명령 큐 삭제
commandsRouter.delete('/bulk', requireAdmin, zValidator('json', z.object({ pc_ids: z.array(z.number().int()) })), async (c) => {
  const { pc_ids } = c.req.valid('json')
  db.delete(commands)
    .where(and(inArray(commands.pcId, pc_ids), eq(commands.status, 'pending')))
    .run()
  return c.json({ status: 'ok' })
})