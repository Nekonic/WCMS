import { createMiddleware } from 'hono/factory'
import { getCookie, setCookie, deleteCookie } from 'hono/cookie'
import { createHmac, timingSafeEqual } from 'crypto'

const SECRET = process.env.WCMS_SECRET_KEY ?? 'dev-secret-change-in-production'
const COOKIE_NAME = 'wcms_session'
const MAX_AGE = 60 * 60 * 8  // 8시간

export type SessionPayload = {
  adminId: number
  username: string
}

// HMAC-SHA256으로 세션 쿠키 서명
function sign(payload: SessionPayload): string {
  const data = JSON.stringify(payload)
  const encoded = Buffer.from(data).toString('base64url')
  const sig = createHmac('sha256', SECRET).update(encoded).digest('base64url')
  return `${encoded}.${sig}`
}

function verify(cookie: string): SessionPayload | null {
  const parts = cookie.split('.')
  if (parts.length !== 2) return null
  const [encoded, sig] = parts
  const expected = createHmac('sha256', SECRET).update(encoded).digest('base64url')
  try {
    if (!timingSafeEqual(Buffer.from(sig), Buffer.from(expected))) return null
  } catch {
    return null
  }
  try {
    return JSON.parse(Buffer.from(encoded, 'base64url').toString()) as SessionPayload
  } catch {
    return null
  }
}

// 세션 쿠키 발급
export function setSession(c: Parameters<typeof setCookie>[0], payload: SessionPayload) {
  setCookie(c, COOKIE_NAME, sign(payload), {
    httpOnly: true,
    sameSite: 'Lax',
    path: '/',
    maxAge: MAX_AGE,
    secure: process.env.NODE_ENV === 'production',
  })
}

// 세션 쿠키 삭제
export function clearSession(c: Parameters<typeof deleteCookie>[0]) {
  deleteCookie(c, COOKIE_NAME, { path: '/' })
}

// 현재 세션 읽기 (없으면 null)
export function getSession(c: Parameters<typeof getCookie>[0]): SessionPayload | null {
  const cookie = getCookie(c, COOKIE_NAME)
  if (!cookie) return null
  return verify(cookie)
}

// 관리자 인증 미들웨어 — 라우트에 직접 적용
export const requireAdmin = createMiddleware(async (c, next) => {
  const session = getSession(c)
  if (!session) {
    return c.json({ status: 'error', message: 'Unauthorized' }, 401)
  }
  c.set('session', session)
  await next()
})

// Hono context 타입 확장
declare module 'hono' {
  interface ContextVariableMap {
    session: SessionPayload
  }
}