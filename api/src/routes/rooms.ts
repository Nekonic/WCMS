import { Hono } from 'hono'
import { zValidator } from '@hono/zod-validator'
import { z } from 'zod'
import { eq } from 'drizzle-orm'
import type { DB } from '../db/index.js'
import { seatLayout, seatMap, pcInfo } from '../db/schema.js'
import { requireAdmin } from '../middleware/auth.js'

export function createRoomsRouter(db: DB) {
  const router = new Hono()

  const RoomSchema = z.object({
    room_name:   z.string().min(1),
    rows:        z.number().int().min(1).max(20),
    cols:        z.number().int().min(1).max(20),
    description: z.string().optional(),
  })

  // 실습실 목록
  router.get('/', async (c) => {
    const rooms = db.select().from(seatLayout).where(eq(seatLayout.isActive, true)).all()
    return c.json(rooms)
  })

  // 실습실 생성
  router.post('/', requireAdmin, zValidator('json', RoomSchema), async (c) => {
    const data = c.req.valid('json')
    db.insert(seatLayout).values({
      roomName:    data.room_name,
      rows:        data.rows,
      cols:        data.cols,
      description: data.description,
    }).run()
    return c.json({ status: 'ok' }, 201)
  })

  // 실습실 수정
  router.put('/:id', requireAdmin, zValidator('json', RoomSchema.partial()), async (c) => {
    const id = Number(c.req.param('id'))
    const data = c.req.valid('json')
    db.update(seatLayout).set({
      ...(data.rows        && { rows: data.rows }),
      ...(data.cols        && { cols: data.cols }),
      ...(data.description && { description: data.description }),
      updatedAt: new Date().toISOString(),
    }).where(eq(seatLayout.id, id)).run()
    return c.json({ status: 'ok' })
  })

  // 실습실 삭제
  router.delete('/:id', requireAdmin, async (c) => {
    const id = Number(c.req.param('id'))
    db.update(seatLayout).set({ isActive: false }).where(eq(seatLayout.id, id)).run()
    return c.json({ status: 'ok' })
  })

  // ==================== 좌석 배치 ====================

  // 좌석 배치 조회 (공개 — Svelte 메인 화면)
  router.get('/:room/layout', async (c) => {
    const roomName = c.req.param('room')

    const room = db.select().from(seatLayout).where(eq(seatLayout.roomName, roomName)).get()
    if (!room) return c.json({ error: 'Room not found' }, 404)

    const seats = db.select({
      row:      seatMap.row,
      col:      seatMap.col,
      pcId:     seatMap.pcId,
      hostname: pcInfo.hostname,
      isOnline: pcInfo.isOnline,
    })
      .from(seatMap)
      .leftJoin(pcInfo, eq(seatMap.pcId, pcInfo.id))
      .where(eq(seatMap.roomName, roomName))
      .all()

    return c.json({ room, seats })
  })

  // 좌석 배치 저장 (관리자)
  const LayoutSaveSchema = z.array(z.object({
    row:   z.number().int(),
    col:   z.number().int(),
    pc_id: z.number().int().nullable(),
  }))

  router.post('/:room/layout', requireAdmin, zValidator('json', LayoutSaveSchema), async (c) => {
    const roomName = c.req.param('room')
    const seats = c.req.valid('json')

    // 기존 좌석 맵 삭제 후 재삽입
    db.delete(seatMap).where(eq(seatMap.roomName, roomName)).run()

    for (const seat of seats) {
      if (seat.pc_id !== null) {
        db.insert(seatMap).values({
          roomName,
          row:  seat.row,
          col:  seat.col,
          pcId: seat.pc_id,
        }).run()

        // pc_info에 room_name, seat_number 기록
        db.update(pcInfo).set({
          roomName:   roomName,
          seatNumber: `${seat.row}, ${seat.col}`,
        }).where(eq(pcInfo.id, seat.pc_id)).run()
      }
    }

    return c.json({ status: 'ok' })
  })

  return router
}