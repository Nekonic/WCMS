import { Hono } from 'hono'
import { zValidator } from '@hono/zod-validator'
import { z } from 'zod'
import { eq, and, desc, isNull } from 'drizzle-orm'
import type { DB } from '../db/index.js'
import { pcInfo, pcSpecs, pcDynamicInfo, commands, pcRegistrationTokens, networkEvents, clientVersions } from '../db/schema.js'

const OFFLINE_THRESHOLD_SEC = 40  // 이 시간 동안 heartbeat 없으면 오프라인
const LONG_POLL_TIMEOUT_SEC = 30

export function createClientRouter(db: DB) {
  const router = new Hono()

  // ==================== PC 등록 ====================

  const RegisterSchema = z.object({
    machine_id:  z.string().min(1),
    pin:         z.string().length(6),
    hostname:    z.string().optional(),
    mac_address: z.string().optional(),
    ip_address:  z.string().optional(),
    cpu_model:   z.string().optional(),
    cpu_cores:   z.number().int().optional(),
    cpu_threads: z.number().int().optional(),
    ram_total:   z.number().optional(),
    disk_info:   z.string().optional(),  // JSON string
    os_edition:  z.string().optional(),
    os_version:  z.string().optional(),
  })

  router.post('/register', zValidator('json', RegisterSchema), async (c) => {
    const data = c.req.valid('json')

    // PIN 검증
    const token = db.select().from(pcRegistrationTokens)
      .where(eq(pcRegistrationTokens.token, data.pin))
      .get()

    if (!token) {
      return c.json({ status: 'error', message: 'Invalid PIN' }, 403)
    }
    if (token.isExpired) {
      return c.json({ status: 'error', message: 'PIN has been manually expired' }, 403)
    }
    if (new Date() > new Date(token.expiresAt)) {
      return c.json({ status: 'error', message: 'PIN expired' }, 403)
    }
    if (token.usageType === 'single' && (token.usedCount ?? 0) > 0) {
      return c.json({ status: 'error', message: 'PIN already used (single-use token)' }, 403)
    }

    // PC 등록 or 업데이트
    const existing = db.select({ id: pcInfo.id })
      .from(pcInfo).where(eq(pcInfo.machineId, data.machine_id)).get()

    let pcId: number
    const now = new Date().toISOString()

    if (existing) {
      pcId = existing.id
      db.update(pcInfo).set({
        hostname:            data.hostname ?? 'Unknown-PC',
        macAddress:          data.mac_address ?? '00:00:00:00:00:00',
        ipAddress:           data.ip_address,
        isVerified:          true,
        registeredWithToken: data.pin,
        verifiedAt:          now,
      }).where(eq(pcInfo.id, pcId)).run()
    } else {
      const result = db.insert(pcInfo).values({
        machineId:           data.machine_id,
        hostname:            data.hostname ?? 'Unknown-PC',
        macAddress:          data.mac_address ?? '00:00:00:00:00:00',
        ipAddress:           data.ip_address,
        isVerified:          true,
        registeredWithToken: data.pin,
        verifiedAt:          now,
      }).returning({ id: pcInfo.id }).get()
      pcId = result.id
    }

    // 스펙 저장
    if (data.cpu_model) {
      const existingSpec = db.select({ id: pcSpecs.id }).from(pcSpecs).where(eq(pcSpecs.pcId, pcId)).get()
      const specData = {
        cpuModel:   data.cpu_model,
        cpuCores:   data.cpu_cores ?? 0,
        cpuThreads: data.cpu_threads ?? 0,
        ramTotal:   data.ram_total ?? 0,
        diskInfo:   data.disk_info ?? '{}',
        osEdition:  data.os_edition ?? '',
        osVersion:  data.os_version ?? '',
      }
      if (existingSpec) {
        db.update(pcSpecs).set(specData).where(eq(pcSpecs.pcId, pcId)).run()
      } else {
        db.insert(pcSpecs).values({ pcId, ...specData }).run()
      }
    }

    // 토큰 사용 횟수 증가
    db.update(pcRegistrationTokens).set({
      usedCount: (token.usedCount ?? 0) + 1,
    }).where(eq(pcRegistrationTokens.id, token.id)).run()

    return c.json({ status: 'success', pc_id: pcId })
  })

  // ==================== Heartbeat ====================

  const HeartbeatSchema = z.object({
    machine_id:       z.string(),
    cpu_usage:        z.number(),
    ram_used:         z.number(),
    ram_usage_percent: z.number(),
    disk_usage:       z.string().optional(),
    current_user:     z.string().optional(),
    uptime:           z.number().int(),
    processes:        z.string().optional(),
    ip_address:       z.string().optional(),
  })

  router.post('/heartbeat', zValidator('json', HeartbeatSchema), async (c) => {
    const data = c.req.valid('json')

    const pc = db.select({ id: pcInfo.id }).from(pcInfo)
      .where(and(eq(pcInfo.machineId, data.machine_id), eq(pcInfo.isVerified, true))).get()

    if (!pc) {
      return c.json({ status: 'error', message: 'PC not registered' }, 404)
    }

    // ip_address 업데이트
    if (data.ip_address) {
      db.update(pcInfo).set({ ipAddress: data.ip_address }).where(eq(pcInfo.id, pc.id)).run()
    }

    // 동적 상태 upsert
    const existing = db.select({ id: pcDynamicInfo.id }).from(pcDynamicInfo)
      .where(eq(pcDynamicInfo.pcId, pc.id)).get()

    const dynData = {
      cpuUsage:        data.cpu_usage,
      ramUsed:         data.ram_used,
      ramUsagePercent: data.ram_usage_percent,
      diskUsage:       data.disk_usage,
      currentUser:     data.current_user,
      uptime:          data.uptime,
      processes:       data.processes,
      updatedAt:       new Date().toISOString(),
    }

    if (existing) {
      db.update(pcDynamicInfo).set(dynData).where(eq(pcDynamicInfo.pcId, pc.id)).run()
    } else {
      db.insert(pcDynamicInfo).values({ pcId: pc.id, ...dynData }).run()
    }

    // 열린 network_event 닫기 (재연결)
    const openEvent = db.select({ id: networkEvents.id, offlineAt: networkEvents.offlineAt })
      .from(networkEvents)
      .where(and(eq(networkEvents.pcId, pc.id), isNull(networkEvents.onlineAt)))
      .get()

    if (openEvent) {
      const durationSec = Math.floor(
        (Date.now() - new Date(openEvent.offlineAt).getTime()) / 1000
      )
      db.update(networkEvents).set({
        onlineAt: new Date().toISOString(),
        durationSec,
      }).where(eq(networkEvents.id, openEvent.id)).run()
    }

    return c.json({ status: 'ok' })
  })

  // ==================== Long-poll 명령 대기 ====================

  router.get('/commands', async (c) => {
    const machineId = c.req.query('machine_id')
    const timeoutSec = Math.min(Number(c.req.query('timeout') ?? LONG_POLL_TIMEOUT_SEC), 60)

    if (!machineId) {
      return c.json({ status: 'error', message: 'machine_id required' }, 400)
    }

    const pc = db.select({ id: pcInfo.id }).from(pcInfo)
      .where(and(eq(pcInfo.machineId, machineId), eq(pcInfo.isVerified, true))).get()

    if (!pc) {
      return c.json({ status: 'error', message: 'PC not registered' }, 404)
    }

    const deadline = Date.now() + timeoutSec * 1000

    // 대기 중인 명령이 생길 때까지 polling
    while (Date.now() < deadline) {
      const pending = db.select().from(commands)
        .where(and(eq(commands.pcId, pc.id), eq(commands.status, 'pending')))
        .orderBy(commands.priority, commands.createdAt)
        .limit(1)
        .get()

      if (pending) {
        db.update(commands).set({ status: 'executing' }).where(eq(commands.id, pending.id)).run()
        return c.json({
          status: 'command',
          command: {
            id:           pending.id,
            command_type: pending.commandType,
            command_data: pending.commandData ? JSON.parse(pending.commandData) : {},
            timeout:      pending.timeoutSeconds,
          },
        })
      }

      await new Promise(r => setTimeout(r, 2000))
    }

    return c.json({ status: 'no_command' })
  })

  // ==================== 명령 결과 제출 ====================

  const CommandResultSchema = z.object({
    machine_id: z.string(),
    result:     z.string().optional(),
    status:     z.enum(['completed', 'error']),
    error:      z.string().optional(),
  })

  router.post('/commands/:id/result', zValidator('json', CommandResultSchema), async (c) => {
    const commandId = Number(c.req.param('id'))
    const data = c.req.valid('json')

    db.update(commands).set({
      status:       data.status,
      result:       data.result,
      errorMessage: data.error,
      completedAt:  new Date().toISOString(),
    }).where(eq(commands.id, commandId)).run()

    return c.json({ status: 'ok' })
  })

  // ==================== 오프라인 신호 ====================

  const OfflineSchema = z.object({
    machine_id: z.string(),
    reason:     z.enum(['shutdown', 'network_error', 'unknown']).default('unknown'),
  })

  router.post('/offline', zValidator('json', OfflineSchema), async (c) => {
    const data = c.req.valid('json')

    const pc = db.select({ id: pcInfo.id }).from(pcInfo)
      .where(eq(pcInfo.machineId, data.machine_id)).get()

    if (!pc) return c.json({ status: 'ok' })

    db.update(pcInfo).set({ isOnline: false }).where(eq(pcInfo.id, pc.id)).run()

    // network_event 기록 (이미 열린 것이 없으면)
    const existing = db.select({ id: networkEvents.id }).from(networkEvents)
      .where(and(eq(networkEvents.pcId, pc.id), isNull(networkEvents.onlineAt))).get()

    if (!existing) {
      db.insert(networkEvents).values({
        pcId:      pc.id,
        offlineAt: new Date().toISOString(),
        reason:    data.reason,
      }).run()
    }

    return c.json({ status: 'ok' })
  })

  // ==================== 종료 신호 ====================

  router.post('/shutdown', zValidator('json', z.object({ machine_id: z.string() })), async (c) => {
    const { machine_id } = c.req.valid('json')
    const pc = db.select({ id: pcInfo.id }).from(pcInfo).where(eq(pcInfo.machineId, machine_id)).get()
    if (pc) {
      db.update(pcInfo).set({ isOnline: false }).where(eq(pcInfo.id, pc.id)).run()
    }
    return c.json({ status: 'ok' })
  })

  // ==================== 최신 클라이언트 버전 ====================

  router.get('/version', async (c) => {
    const latest = db.select().from(clientVersions)
      .orderBy(desc(clientVersions.releasedAt)).limit(1).get()

    if (!latest) return c.json({ version: null })
    return c.json({
      version:      latest.version,
      download_url: latest.downloadUrl,
      changelog:    latest.changelog,
    })
  })

  // GitHub Actions에서 새 버전 등록
  const VersionSchema = z.object({
    version:      z.string(),
    download_url: z.string().optional(),
    changelog:    z.string().optional(),
  })

  router.post('/version', async (c) => {
    const authHeader = c.req.header('Authorization')
    const UPDATE_TOKEN = process.env.WCMS_UPDATE_TOKEN
    if (!UPDATE_TOKEN || authHeader !== `Bearer ${UPDATE_TOKEN}`) {
      return c.json({ status: 'error', message: 'Unauthorized' }, 401)
    }

    const body = await c.req.json()
    const parsed = VersionSchema.safeParse(body)
    if (!parsed.success) return c.json({ status: 'error', message: 'Invalid body' }, 400)

    db.insert(clientVersions).values({
      version:     parsed.data.version,
      downloadUrl: parsed.data.download_url,
      changelog:   parsed.data.changelog,
    }).run()

    return c.json({ status: 'ok' })
  })

  return router
}