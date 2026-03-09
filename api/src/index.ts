import { serve } from '@hono/node-server'
import { serveStatic } from '@hono/node-server/serve-static'
import { Hono } from 'hono'
import { cors } from 'hono/cors'
import { logger } from 'hono/logger'
import { secureHeaders } from 'hono/secure-headers'

import { db } from './db/index.js'
import { createClientRouter }   from './routes/client.js'
import { createAdminRouter }    from './routes/admin.js'
import { createPcsRouter }      from './routes/pcs.js'
import { createRoomsRouter }    from './routes/rooms.js'
import { createCommandsRouter } from './routes/commands.js'
import { installRouter }        from './routes/install.js'

const app = new Hono()

// ==================== 미들웨어 ====================

app.use(logger())
app.use(secureHeaders())
app.use('/api/*', cors({
  origin:      process.env.WCMS_ALLOWED_ORIGINS?.split(',') ?? '*',
  credentials: true,
}))

// ==================== 라우트 ====================

app.route('/api/client',   createClientRouter(db))
app.route('/api/admin',    createAdminRouter(db))
app.route('/api/pcs',      createPcsRouter(db))
app.route('/api/rooms',    createRoomsRouter(db))
app.route('/api/commands', createCommandsRouter(db))
app.route('/install',      installRouter)

// 헬스 체크
app.get('/health', (c) => c.json({ status: 'ok', ts: new Date().toISOString() }))

// 프론트엔드 정적 파일 (../frontend/build — npm run build 후 생성)
app.use('/*', serveStatic({ root: '../frontend/build' }))
app.use('/*', serveStatic({ path: '../frontend/build/index.html' }))

// 404
app.notFound((c) => c.json({ error: 'Not found' }, 404))

// ==================== 서버 시작 ====================

const PORT = Number(process.env.PORT ?? 5050)
const HOST = process.env.HOST ?? '0.0.0.0'

if (process.env.WCMS_SECRET_KEY === 'dev-secret-change-in-production' || !process.env.WCMS_SECRET_KEY) {
  console.warn('[WARN] WCMS_SECRET_KEY가 설정되지 않았습니다. 프로덕션에서는 반드시 설정하세요.')
}

serve({ fetch: app.fetch, port: PORT, hostname: HOST }, (info) => {
  console.log(`WCMS API server running on http://${HOST}:${info.port}`)
})

export default app