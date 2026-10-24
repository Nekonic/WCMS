# WCMS 2026.1 계획 03: 프론트엔드 기반 (SvelteKit SPA) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 계획 02 서버 위에 관리자·비로그인 웹 화면을 SvelteKit SPA로 만든다. 범위: 로그인(비밀번호 → 인증 코드), 등록 링크, 실습실 실시간 그리드(관리자/비로그인), 설정 화면(실습실·좌석, PC, 등록 PIN, 관리자 계정, 기록).

**Architecture:** 저장소 루트 `frontend/`. SvelteKit 2 + Svelte 5 + TypeScript, adapter-static으로 SPA 빌드(모든 경로 index.html). REST는 `server/openapi.yaml`에서 생성한 타입 + openapi-fetch 래퍼(`src/lib/api`), 실시간은 WebSocket 하나를 쓰는 `src/lib/live`. 실시간 상태는 `lib/live`에서만 다루고 REST는 CRUD와 기록 조회에만 쓴다. 스타일은 Tailwind CSS v4, 화면 예시의 색을 토큰으로.

**Tech Stack:** Node 22 이상, pnpm, SvelteKit 2, Svelte 5(runes), TypeScript, Vite, @sveltejs/adapter-static, Tailwind CSS v4(@tailwindcss/vite), openapi-typescript, openapi-fetch, vitest, svelte-check

**선행 조건:** 계획 02 완료 (`server/openapi.yaml`, `/api/*`, `/ws/live`)

**설계 문서:** `docs/superpowers/specs/2026-10-24-wcms-2026-1-design.md` (2장 "웹 구조", 3.8, 3.9, 8장)

**작업 브랜치:** `dev`에서 `feat/frontend-base`

**이 계획에서 하지 않는 것:** 좌석 칸 우클릭 메뉴, 드래그·Shift 선택, 명령 실행 확인 창은 명령 기능과 함께 계획 04에서 한다. PC 상세 화면, 화면 썸네일도 계획 04·06.

## Global Constraints

- 패키지 관리는 pnpm, Node 22 이상. 명령은 모두 `frontend/`에서 실행한다.
- 서버 API 타입은 손으로 쓰지 않는다. `pnpm gen:api`로 `server/openapi.yaml`에서 `src/lib/api/schema.d.ts`를 생성하고 커밋한다. WebSocket 메시지 유니온 타입만 손으로 쓴다(`src/lib/live/types.ts`).
- 학생이 조작할 수 있는 값(호스트 이름, 사용자 이름, 창 제목, 프로세스 이름)은 Svelte 텍스트 보간으로만 출력한다. `{@html}` 금지. 예외는 서버가 만든 등록용 QR SVG 하나.
- 비로그인 화면은 `/api/public/*`와 `room:<id>:public` 구독만 쓴다. 좌석 라벨과 켜짐/꺼짐 외에는 보여주지 않는다.
- 변경 요청(POST/PUT/PATCH/DELETE)에는 `csrftoken` 쿠키 값을 `X-CSRFToken` 헤더로 붙인다. 쿠키는 요청할 때마다 다시 읽는다.
- `/api/auth/*`가 아닌 API가 401을 주면 `/login?next=<현재 경로>`로 보낸다. `next`는 `/`로 시작하고 `//`로 시작하지 않을 때만 따른다.
- 시각은 서버에서 UTC로 받아 화면에서 `Asia/Seoul`로 표시한다.
- 화면 언어는 한국어만.
- 지우기, 폐기, 재설정처럼 되돌리기 어려운 동작은 확인 창을 거친다.
- 커밋 메시지에 작성자 표기(Co-Authored-By 등)를 넣지 않는다.

---

## 파일 구조

```
frontend/
  package.json, pnpm-lock.yaml, svelte.config.js, vite.config.ts, tsconfig.json
  src/
    app.html, app.css, app.d.ts
    lib/
      api/schema.d.ts        생성물 (커밋)
      api/types.ts           생성 타입의 별칭 (LivePC, PublicSeat, ...)
      api/csrf.ts            csrftoken 쿠키 읽기
      api/client.ts          openapi-fetch 클라이언트 + CSRF + 401 처리
      api/errors.ts          오류 메시지, 입력 오류 꺼내기
      nav.ts                 safeNext
      format.ts              시각 표시 (Asia/Seoul)
      grid.ts                좌석 격자 계산
      pcState.ts             관리자용 PC 상태 표시
      live/types.ts          WebSocket 메시지 유니온
      live/socket.ts         LiveSocket (연결 하나, 구독 참조 카운트, 재접속)
      live/merge.ts          스냅샷·변경 합치기
      live/index.ts          앱 전체에서 쓰는 LiveSocket 하나
      components/SeatGrid.svelte, AdminTile.svelte, PublicTile.svelte, ConfirmButton.svelte
    routes/
      +layout.ts, +layout.svelte, +page.ts, +page.svelte
      login/+page.svelte
      enroll/[token]/+page.ts, +page.svelte
      rooms/[id]/+page.ts, +page.svelte
      settings/+layout.ts
      settings/rooms/+page.ts, +page.svelte
      settings/rooms/[id]/+page.ts, +page.svelte
      settings/pcs/+page.ts, +page.svelte
      settings/pins/+page.ts, +page.svelte
      settings/admins/+page.ts, +page.svelte
      settings/audit/+page.svelte
    **/*.test.ts             vitest (lib만)
```

---

### Task 1: 프로젝트 골격, Tailwind 토큰, 빌드

**Files:**
- Create: `frontend/package.json`, `frontend/svelte.config.js`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/src/app.html`, `frontend/src/app.css`, `frontend/src/app.d.ts`, `frontend/src/routes/+layout.ts`, `frontend/src/routes/+layout.svelte`, `frontend/src/routes/+page.svelte`
- Modify: `.gitignore`

**Interfaces:**
- Produces:
  - 스크립트: `pnpm dev`(5173, `/api` `/client` `/ws`를 `localhost:8000`으로 프록시), `pnpm build`(→ `build/index.html`), `pnpm check`(svelte-check), `pnpm test`(vitest), `pnpm gen:api`
  - Tailwind 토큰 색: `ground, surface, ink, muted, line, line-soft, side, side-ink, side-muted, side-hover, side-on, accent, accent-dark, ok, danger, danger-soft, warn, warn-soft`
  - 컴포넌트 클래스: `btn`, `btn-primary`, `btn-danger`, `btn-sm`, `card`, `field`, `label`, `error-box`, `notice-box`, `page-title`, `meta`
  - 루트 레이아웃: `ssr = false`, `prerender = false`

- [ ] **Step 1: package.json과 의존성**

`frontend/package.json`:

```json
{
  "name": "wcms-frontend",
  "version": "2026.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite dev",
    "build": "vite build",
    "preview": "vite preview",
    "check": "svelte-kit sync && svelte-check --tsconfig ./tsconfig.json --fail-on-warnings",
    "test": "vitest run",
    "gen:api": "openapi-typescript ../server/openapi.yaml -o src/lib/api/schema.d.ts"
  }
}
```

```bash
cd frontend
pnpm add -D @sveltejs/kit@^2 @sveltejs/adapter-static@^3 @sveltejs/vite-plugin-svelte svelte@^5 svelte-check typescript@^5 vite tailwindcss@^4 @tailwindcss/vite@^4 vitest openapi-typescript@^7
pnpm add openapi-fetch
pnpm peers check
```

Expected: `pnpm-lock.yaml` 생성, `pnpm peers check`에 맞지 않는 peer가 없다. 남으면 그 패키지를 peer 범위에 맞는 메이저로 고정해 다시 설치한다 (kit 3, adapter-static 4, TypeScript 7은 쓰지 않는다).

- [ ] **Step 2: 설정 파일**

`frontend/svelte.config.js`:

```js
import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
export default {
	preprocess: vitePreprocess(),
	kit: {
		adapter: adapter({ fallback: 'index.html' })
	}
};
```

`frontend/vite.config.ts`:

```ts
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vitest/config';

const backend = 'http://localhost:8000';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	server: {
		port: 5173,
		proxy: {
			'/api': backend,
			'/client': backend,
			'/ws': { target: backend, ws: true }
		}
	},
	test: {
		include: ['src/**/*.test.ts'],
		environment: 'node'
	}
});
```

`frontend/tsconfig.json`:

```json
{
	"extends": "./.svelte-kit/tsconfig.json",
	"compilerOptions": {
		"allowJs": true,
		"checkJs": true,
		"esModuleInterop": true,
		"forceConsistentCasingInFileNames": true,
		"resolveJsonModule": true,
		"skipLibCheck": true,
		"sourceMap": true,
		"strict": true,
		"moduleResolution": "bundler",
		"verbatimModuleSyntax": true
	}
}
```

`frontend/src/app.d.ts`:

```ts
declare global {
	namespace App {}
}

export {};
```

`frontend/src/app.html`:

```html
<!doctype html>
<html lang="ko">
	<head>
		<meta charset="utf-8" />
		<meta name="viewport" content="width=device-width, initial-scale=1" />
		<link rel="preconnect" href="https://fonts.googleapis.com" />
		<link
			rel="stylesheet"
			href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"
		/>
		<title>WCMS</title>
		%sveltekit.head%
	</head>
	<body data-sveltekit-preload-data="hover">
		<div style="display: contents">%sveltekit.body%</div>
	</body>
</html>
```

`frontend/src/app.css`:

```css
@import 'tailwindcss';

@theme {
	--font-sans: 'IBM Plex Sans KR', system-ui, sans-serif;
	--font-mono: 'JetBrains Mono', ui-monospace, monospace;

	--color-ground: #f4f5f7;
	--color-surface: #ffffff;
	--color-ink: #15171c;
	--color-muted: #5b616e;
	--color-line: #e1e4ea;
	--color-line-soft: #eef0f3;
	--color-side: #111318;
	--color-side-ink: #c9cdd6;
	--color-side-muted: #8b919e;
	--color-side-hover: #1c1f26;
	--color-side-on: #262a36;
	--color-accent: #2449d8;
	--color-accent-dark: #1a36a8;
	--color-ok: #13804a;
	--color-danger: #b42318;
	--color-danger-soft: #fce9e7;
	--color-warn: #8a3a00;
	--color-warn-soft: #fff4e5;
}

@layer base {
	body {
		@apply bg-ground font-sans text-sm text-ink;
	}
	a {
		@apply text-accent hover:text-accent-dark;
	}
}

@layer components {
	.btn {
		@apply inline-flex min-h-11 cursor-pointer items-center justify-center gap-1.5 rounded-lg border border-[#d5d9e0] bg-surface px-4 font-medium whitespace-nowrap text-ink hover:bg-[#f1f3f6] disabled:cursor-not-allowed disabled:opacity-50;
	}
	.btn-primary {
		@apply border-accent bg-accent text-white hover:bg-accent-dark;
	}
	.btn-danger {
		@apply border-[#ebc3bf] text-danger;
	}
	.btn-sm {
		@apply min-h-9 px-3 text-[13px];
	}
	.card {
		@apply rounded-[14px] border border-line bg-surface p-5;
	}
	.field {
		@apply min-h-11 rounded-lg border border-[#d5d9e0] bg-surface px-3;
	}
	.label {
		@apply text-[13px] font-semibold text-[#3d424d];
	}
	.error-box {
		@apply rounded-lg bg-danger-soft px-3 py-2.5 text-[#a3211a];
	}
	.notice-box {
		@apply rounded-lg bg-[#e6ecfb] px-3 py-2.5 text-accent-dark;
	}
	.page-title {
		@apply text-[26px] font-bold;
	}
	.meta {
		@apply text-muted;
	}
}
```

`frontend/src/routes/+layout.ts`:

```ts
export const ssr = false;
export const prerender = false;
```

`frontend/src/routes/+layout.svelte`:

```svelte
<script lang="ts">
	import '../app.css';
	import type { Snippet } from 'svelte';

	let { children }: { children: Snippet } = $props();
</script>

{@render children()}
```

`frontend/src/routes/+page.svelte`:

```svelte
<h1 class="page-title">WCMS</h1>
```

`.gitignore`에 추가:

```
frontend/node_modules/
frontend/.svelte-kit/
frontend/build/
```

- [ ] **Step 3: 확인**

Run: `pnpm check && pnpm build && ls build/index.html`
Expected: svelte-check 오류·경고 0, 빌드 성공, `build/index.html` 존재

- [ ] **Step 4: Commit**

```bash
git add frontend .gitignore
git commit -m "feat(frontend): SvelteKit SPA skeleton with Tailwind tokens"
```

---

### Task 2: API 계층 (생성 타입, 클라이언트, CSRF, 오류)

**Files:**
- Create: `frontend/src/lib/api/schema.d.ts` (생성), `frontend/src/lib/api/types.ts`, `frontend/src/lib/api/csrf.ts`, `frontend/src/lib/api/client.ts`, `frontend/src/lib/api/errors.ts`, `frontend/src/lib/nav.ts`, `frontend/src/lib/format.ts`
- Test: `frontend/src/lib/api/csrf.test.ts`, `frontend/src/lib/api/errors.test.ts`, `frontend/src/lib/nav.test.ts`, `frontend/src/lib/format.test.ts`

**Interfaces:**
- Consumes: `server/openapi.yaml`
- Produces:
  - `$lib/api/types`: `LivePC`, `PublicSeat`, `PublicRoom`, `Room`, `PC`, `Pin`, `Admin`, `Me`, `ApiErrorBody`, `AuditLog`, `EnrollInfo`
  - `$lib/api/csrf.csrfToken(cookie: string): string | null`
  - `$lib/api/client.api` (openapi-fetch 클라이언트. 변경 요청에 X-CSRFToken, `/api/auth/*` 외 401이면 로그인 화면으로)
  - `$lib/api/errors.errorMessage(error: unknown): string`, `fieldErrors(error: unknown): Record<string, string>`
  - `$lib/nav.safeNext(value: string | null): string`
  - `$lib/format.formatTime(iso: string): string` (Asia/Seoul, `2026. 10. 25. 오후 3:04` 형태)

- [ ] **Step 1: 타입 생성**

Run: `pnpm gen:api`
Expected: `src/lib/api/schema.d.ts` 생성. `grep -c "LivePC" src/lib/api/schema.d.ts`가 1 이상.

- [ ] **Step 2: 실패하는 테스트 작성**

`frontend/src/lib/api/csrf.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { csrfToken } from './csrf';

describe('csrfToken', () => {
	it('reads the csrftoken cookie', () => {
		expect(csrfToken('a=1; csrftoken=abc%3D; b=2')).toBe('abc=');
	});
	it('returns null when missing', () => {
		expect(csrfToken('sessionid=x')).toBeNull();
		expect(csrfToken('')).toBeNull();
	});
});
```

`frontend/src/lib/api/errors.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { errorMessage, fieldErrors } from './errors';

describe('errorMessage', () => {
	it('uses the server detail', () => {
		expect(errorMessage({ error: 'invalid_code', detail: '인증 코드가 올바르지 않습니다.' })).toBe(
			'인증 코드가 올바르지 않습니다.'
		);
	});
	it('falls back for unknown shapes', () => {
		expect(errorMessage(undefined)).toBe('요청을 처리하지 못했습니다.');
		expect(errorMessage('boom')).toBe('요청을 처리하지 못했습니다.');
	});
});

describe('fieldErrors', () => {
	it('flattens field error lists', () => {
		expect(
			fieldErrors({ error: 'invalid', detail: 'x', fields: { password: ['짧습니다.', '흔합니다.'], seats: 'x' } })
		).toEqual({ password: '짧습니다. 흔합니다.', seats: 'x' });
	});
	it('returns empty object without fields', () => {
		expect(fieldErrors({ error: 'x', detail: 'y' })).toEqual({});
	});
	it('uses a generic message for nested item errors', () => {
		expect(fieldErrors({ error: 'invalid', detail: 'x', fields: { seats: [{}, { pc: ['없는 PC'] }] } })).toEqual({
			seats: '입력값을 확인하세요.'
		});
	});
});
```

`frontend/src/lib/nav.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { safeNext } from './nav';

describe('safeNext', () => {
	it('keeps local paths', () => {
		expect(safeNext('/settings/pins?x=1')).toBe('/settings/pins?x=1');
	});
	it('rejects external or missing targets', () => {
		for (const value of [null, '', 'https://evil.example', '//evil.example', '/\\evil.example', 'settings']) {
			expect(safeNext(value)).toBe('/');
		}
	});
});
```

`frontend/src/lib/format.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { formatTime } from './format';

describe('formatTime', () => {
	it('shows Asia/Seoul time', () => {
		expect(formatTime('2026-10-25T06:04:00Z')).toContain('3:04');
	});
});
```

- [ ] **Step 3: 테스트가 실패하는지 확인**

Run: `pnpm test`
Expected: FAIL, 모듈 없음

- [ ] **Step 4: 구현**

`frontend/src/lib/api/types.ts`:

```ts
import type { components } from './schema';

type Schemas = components['schemas'];

export type LivePC = Schemas['LivePC'];
export type PublicSeat = Schemas['PublicSeat'];
export type PublicRoom = Schemas['PublicRoom'];
export type Room = Schemas['Room'];
export type PC = Schemas['PC'];
export type Pin = Schemas['Pin'];
export type Admin = Schemas['Admin'];
export type Me = Schemas['Me'];
export type AuditLog = Schemas['AuditLog'];
export type EnrollInfo = Schemas['EnrollInfo'];
export type ApiErrorBody = Schemas['Error'];
```

이름이 생성 결과와 다르면(`schema.d.ts`의 `components.schemas` 키를 확인) 생성 결과에 맞춘다. 서버 serializer 이름에서 `Serializer`를 뺀 이름이다.

`frontend/src/lib/api/csrf.ts`:

```ts
export function csrfToken(cookie: string): string | null {
	for (const part of cookie.split(';')) {
		const [name, ...rest] = part.trim().split('=');
		if (name === 'csrftoken') {
			return decodeURIComponent(rest.join('='));
		}
	}
	return null;
}
```

`frontend/src/lib/api/errors.ts`:

```ts
const FALLBACK = '요청을 처리하지 못했습니다.';

function isRecord(value: unknown): value is Record<string, unknown> {
	return typeof value === 'object' && value !== null;
}

export function errorMessage(error: unknown): string {
	if (isRecord(error) && typeof error.detail === 'string' && error.detail) {
		return error.detail;
	}
	return FALLBACK;
}

export function fieldErrors(error: unknown): Record<string, string> {
	if (!isRecord(error) || !isRecord(error.fields)) {
		return {};
	}
	const result: Record<string, string> = {};
	for (const [field, value] of Object.entries(error.fields)) {
		const texts = (Array.isArray(value) ? value : [value]).filter((item): item is string => typeof item === 'string');
		// 좌석 목록처럼 항목별 오류가 중첩되면 문자열이 없다. 그때는 일반 문구를 쓴다
		result[field] = texts.length ? texts.join(' ') : '입력값을 확인하세요.';
	}
	return result;
}
```

`frontend/src/lib/nav.ts`:

```ts
export function safeNext(value: string | null): string {
	if (value && value.startsWith('/') && !value.startsWith('//') && !value.startsWith('/\\')) {
		return value;
	}
	return '/';
}
```

`frontend/src/lib/format.ts`:

```ts
const formatter = new Intl.DateTimeFormat('ko-KR', {
	timeZone: 'Asia/Seoul',
	dateStyle: 'medium',
	timeStyle: 'short'
});

export function formatTime(iso: string): string {
	return formatter.format(new Date(iso));
}
```

`frontend/src/lib/api/client.ts`:

```ts
import createClient, { type Middleware } from 'openapi-fetch';
import { goto } from '$app/navigation';
import { csrfToken } from './csrf';
import type { paths } from './schema';

const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS']);

const middleware: Middleware = {
	onRequest({ request }) {
		if (!SAFE_METHODS.has(request.method)) {
			const token = csrfToken(document.cookie);
			if (token) {
				request.headers.set('X-CSRFToken', token);
			}
		}
		return request;
	},
	async onResponse({ request, response }) {
		const path = new URL(request.url, location.origin).pathname;
		if (response.status === 401 && !path.startsWith('/api/auth/')) {
			await goto(`/login?next=${encodeURIComponent(location.pathname + location.search)}`);
		}
		return response;
	}
};

export const api = createClient<paths>({ baseUrl: location.origin });
api.use(middleware);
```

`client.ts`는 `$app/navigation`과 `location`을 쓰므로 vitest에서 불러오지 않는다. 순수 로직은 `csrf.ts`, `errors.ts`, `nav.ts`에 둔다.

- [ ] **Step 5: 테스트와 타입 검사**

Run: `pnpm test && pnpm check`
Expected: 테스트 전부 통과, svelte-check 0/0

- [ ] **Step 6: Commit**

```bash
git add frontend
git commit -m "feat(frontend): generated API types and fetch client with CSRF and 401 handling"
```

---

### Task 3: 실시간 계층 (LiveSocket, 합치기, 좌석 격자)

**Files:**
- Create: `frontend/src/lib/live/types.ts`, `frontend/src/lib/live/socket.ts`, `frontend/src/lib/live/merge.ts`, `frontend/src/lib/live/index.ts`, `frontend/src/lib/grid.ts`, `frontend/src/lib/pcState.ts`
- Test: `frontend/src/lib/live/socket.test.ts`, `frontend/src/lib/live/merge.test.ts`, `frontend/src/lib/grid.test.ts`, `frontend/src/lib/pcState.test.ts`

**Interfaces:**
- Consumes: `LivePC`, `PublicSeat` (Task 2), 서버 `/ws/live` 메시지 (`docs/live-ws.md`)
- Produces:
  - `$lib/live/types.ServerMessage` (snapshot pcs/seats/pc, pc, seat, room_changed, error)
  - `$lib/live/socket.LiveSocket(url, create?, onSessionEnd?)`: `subscribe(topic, handler) => unsubscribe`, `close()`. 같은 토픽은 서버에 한 번만 구독, 마지막 해제 때 unsubscribe. 재접속(1초부터 두 배, 최대 30초, 0~1초 무작위)하면 모든 토픽 다시 구독. `room_changed`를 받으면 그 토픽 다시 구독. close code 4401이면 재접속하지 않고 `onSessionEnd` 호출. 연결이 열려 있는 동안 25초마다 `{type: 'ping'}`을 보낸다 (서버가 만료된 그룹 가입을 되살리고 관리자 권한과 세션을 다시 확인한다). `pong`은 무시
  - `$lib/live/socket.SESSION_ENDED = 4401`
  - `$lib/live/merge`: `seatKey(row, col): string`, `adminRoomReducer(current: Map<number, LivePC>, message): Map<number, LivePC>`, `publicRoomReducer(current: Map<string, PublicSeat>, message): Map<string, PublicSeat>` (새 Map을 돌려준다)
  - `$lib/live/index`: `live(): LiveSocket` (앱 전체에 하나), `resetLive(): void` (로그인·로그아웃 뒤 새 세션으로 다시 연결)
  - `$lib/grid`: `type Cell = { kind: 'seat'; row; col; number } | { kind: 'aisle'; key }`, `gridCells(rows, cols, aisleAfter: number | null): Cell[]`, `gridColumns(cols, aisleAfter): string`
  - `$lib/pcState.pcState(pc: LivePC): { key: 'offline' | 'no_user' | 'locked' | 'active'; label: string }`

- [ ] **Step 1: 실패하는 테스트 작성**

`frontend/src/lib/live/socket.test.ts`:

```ts
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { LiveSocket, SESSION_ENDED } from './socket';

class FakeSocket {
	readyState = 0;
	sent: unknown[] = [];
	onopen: ((ev: Event) => unknown) | null = null;
	onmessage: ((ev: MessageEvent) => unknown) | null = null;
	onclose: ((ev: CloseEvent) => unknown) | null = null;
	send(data: string) {
		this.sent.push(JSON.parse(data));
	}
	close() {}
	open() {
		this.readyState = 1;
		this.onopen?.(new Event('open'));
	}
	receive(message: object) {
		this.onmessage?.({ data: JSON.stringify(message) } as MessageEvent);
	}
	drop(code = 1006) {
		this.readyState = 3;
		this.onclose?.({ code } as CloseEvent);
	}
}

let sockets: FakeSocket[];
const create = () => {
	const socket = new FakeSocket();
	sockets.push(socket);
	return socket;
};

beforeEach(() => {
	sockets = [];
	vi.useFakeTimers();
});
afterEach(() => vi.useRealTimers());

describe('LiveSocket', () => {
	it('subscribes once per topic and unsubscribes after the last handler', () => {
		const live = new LiveSocket('ws://x/ws/live', create);
		const off1 = live.subscribe('room:1', () => {});
		const off2 = live.subscribe('room:1', () => {});
		sockets[0].open();
		expect(sockets[0].sent).toEqual([{ type: 'subscribe', topic: 'room:1' }]);
		off1();
		expect(sockets[0].sent).toHaveLength(1);
		off2();
		expect(sockets[0].sent).toEqual([
			{ type: 'subscribe', topic: 'room:1' },
			{ type: 'unsubscribe', topic: 'room:1' }
		]);
	});

	it('routes messages by topic', () => {
		const live = new LiveSocket('ws://x/ws/live', create);
		const a = vi.fn();
		const b = vi.fn();
		live.subscribe('room:1', a);
		live.subscribe('room:2', b);
		sockets[0].open();
		sockets[0].receive({ type: 'pc', topic: 'room:1', pc: { id: 1 } });
		expect(a).toHaveBeenCalledOnce();
		expect(b).not.toHaveBeenCalled();
	});

	it('reconnects with backoff and resubscribes', () => {
		const live = new LiveSocket('ws://x/ws/live', create);
		live.subscribe('room:1', () => {});
		sockets[0].open();
		sockets[0].drop();
		expect(sockets).toHaveLength(1);
		vi.advanceTimersByTime(2100);
		expect(sockets).toHaveLength(2);
		sockets[1].open();
		expect(sockets[1].sent).toEqual([{ type: 'subscribe', topic: 'room:1' }]);
	});

	it('resubscribes on room_changed', () => {
		const live = new LiveSocket('ws://x/ws/live', create);
		live.subscribe('room:1:public', () => {});
		sockets[0].open();
		sockets[0].receive({ type: 'room_changed', topic: 'room:1:public' });
		expect(sockets[0].sent).toEqual([
			{ type: 'subscribe', topic: 'room:1:public' },
			{ type: 'subscribe', topic: 'room:1:public' }
		]);
	});

	it('stops on session end', () => {
		const onEnd = vi.fn();
		const live = new LiveSocket('ws://x/ws/live', create, onEnd);
		live.subscribe('room:1', () => {});
		sockets[0].open();
		sockets[0].drop(SESSION_ENDED);
		vi.advanceTimersByTime(60_000);
		expect(onEnd).toHaveBeenCalledOnce();
		expect(sockets).toHaveLength(1);
	});

	it('pings every 25 seconds while open', () => {
		const live = new LiveSocket('ws://x/ws/live', create);
		live.subscribe('room:1', () => {});
		sockets[0].open();
		vi.advanceTimersByTime(25_000);
		expect(sockets[0].sent).toEqual([
			{ type: 'subscribe', topic: 'room:1' },
			{ type: 'ping' }
		]);
		sockets[0].drop();
		vi.advanceTimersByTime(25_000);
		expect(sockets[0].sent).toHaveLength(2);
	});

	it('close does not report a session end', () => {
		const onEnd = vi.fn();
		const live = new LiveSocket('ws://x/ws/live', create, onEnd);
		live.subscribe('room:1', () => {});
		sockets[0].open();
		const socket = sockets[0];
		live.close();
		socket.drop(SESSION_ENDED);
		expect(onEnd).not.toHaveBeenCalled();
	});

	it('ignores malformed messages', () => {
		const live = new LiveSocket('ws://x/ws/live', create);
		const handler = vi.fn();
		live.subscribe('room:1', handler);
		sockets[0].open();
		sockets[0].onmessage?.({ data: '{nope' } as MessageEvent);
		expect(handler).not.toHaveBeenCalled();
	});
});
```

`frontend/src/lib/live/merge.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import type { LivePC, PublicSeat } from '$lib/api/types';
import { adminRoomReducer, publicRoomReducer, seatKey } from './merge';

const pc = (id: number, online: boolean): LivePC =>
	({ id, online, hostname: `H${id}`, label: `301-0${id}`, room: 1, row: 0, col: id - 1 }) as LivePC;
const seat = (col: number, online: boolean): PublicSeat => ({ row: 0, col, label: `301-0${col + 1}`, online });

describe('adminRoomReducer', () => {
	it('replaces state on snapshot and updates single pcs', () => {
		let state = adminRoomReducer(new Map(), { type: 'snapshot', topic: 'room:1', pcs: [pc(1, false), pc(2, false)] });
		expect(state.size).toBe(2);
		const before = state;
		state = adminRoomReducer(state, { type: 'pc', topic: 'room:1', pc: pc(2, true) });
		expect(state.get(2)?.online).toBe(true);
		expect(state).not.toBe(before);
	});
	it('ignores unrelated messages', () => {
		const state = new Map([[1, pc(1, true)]]);
		expect(adminRoomReducer(state, { type: 'room_changed', topic: 'room:1' })).toBe(state);
	});
});

describe('publicRoomReducer', () => {
	it('keys seats by position', () => {
		let state = publicRoomReducer(new Map(), { type: 'snapshot', topic: 'room:1:public', seats: [seat(0, false)] });
		state = publicRoomReducer(state, { type: 'seat', topic: 'room:1:public', seat: seat(0, true) });
		expect(state.get(seatKey(0, 0))?.online).toBe(true);
	});
});
```

`frontend/src/lib/grid.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import { gridCells, gridColumns } from './grid';

describe('gridCells', () => {
	it('numbers seats row by row and inserts aisles', () => {
		const cells = gridCells(2, 4, 2);
		expect(cells.filter((c) => c.kind === 'aisle')).toHaveLength(2);
		const seats = cells.filter((c) => c.kind === 'seat');
		expect(seats).toHaveLength(8);
		expect(seats[5]).toEqual({ kind: 'seat', row: 1, col: 1, number: 6 });
		expect(cells[2]).toEqual({ kind: 'aisle', key: 'aisle-0' });
	});
	it('has no aisle when aisleAfter is null', () => {
		expect(gridCells(1, 3, null).every((c) => c.kind === 'seat')).toBe(true);
	});
});

describe('gridColumns', () => {
	it('builds the template', () => {
		expect(gridColumns(8, 4)).toBe('repeat(4, minmax(0, 1fr)) 24px repeat(4, minmax(0, 1fr))');
		expect(gridColumns(5, null)).toBe('repeat(5, minmax(0, 1fr))');
	});
});
```

`frontend/src/lib/pcState.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import type { LivePC } from '$lib/api/types';
import { pcState } from './pcState';

const make = (online: boolean, session: LivePC['session']) => ({ online, session }) as LivePC;

describe('pcState', () => {
	it('maps online and session to a display state', () => {
		expect(pcState(make(false, 'active'))).toEqual({ key: 'offline', label: '오프라인' });
		expect(pcState(make(true, 'none'))).toEqual({ key: 'no_user', label: '로그인 없음' });
		expect(pcState(make(true, 'locked'))).toEqual({ key: 'locked', label: '잠금' });
		expect(pcState(make(true, 'active'))).toEqual({ key: 'active', label: '사용 중' });
	});
});
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `pnpm test`
Expected: FAIL, 모듈 없음

- [ ] **Step 3: 구현**

`frontend/src/lib/live/types.ts`:

```ts
import type { LivePC, PublicSeat } from '$lib/api/types';

export type ServerMessage =
	| { type: 'snapshot'; topic: string; pcs: LivePC[] }
	| { type: 'snapshot'; topic: string; seats: PublicSeat[] }
	| { type: 'snapshot'; topic: string; pc: LivePC }
	| { type: 'pc'; topic: string; pc: LivePC }
	| { type: 'seat'; topic: string; seat: PublicSeat }
	| { type: 'room_changed'; topic: string }
	| { type: 'error'; error: string; topic?: string }
	| { type: 'pong' };

export type Handler = (message: ServerMessage) => void;
```

`frontend/src/lib/live/socket.ts`:

```ts
import type { Handler, ServerMessage } from './types';

export const SESSION_ENDED = 4401;
const OPEN = 1;
const MAX_DELAY = 30_000;
const PING_INTERVAL = 25_000;

export interface SocketLike {
	readyState: number;
	send(data: string): void;
	close(): void;
	onopen: ((ev: Event) => unknown) | null;
	onmessage: ((ev: MessageEvent) => unknown) | null;
	onclose: ((ev: CloseEvent) => unknown) | null;
}

export class LiveSocket {
	private socket: SocketLike | null = null;
	private readonly topics = new Map<string, Set<Handler>>();
	private delay = 1000;
	private timer: ReturnType<typeof setTimeout> | null = null;
	private pinger: ReturnType<typeof setInterval> | null = null;
	private stopped = false;

	constructor(
		private readonly url: string,
		private readonly create: (url: string) => SocketLike = (url) => new WebSocket(url),
		private readonly onSessionEnd: () => void = () => {}
	) {}

	subscribe(topic: string, handler: Handler): () => void {
		let handlers = this.topics.get(topic);
		if (!handlers) {
			handlers = new Set();
			this.topics.set(topic, handlers);
			this.send({ type: 'subscribe', topic });
		}
		handlers.add(handler);
		this.ensureOpen();
		return () => {
			const current = this.topics.get(topic);
			if (!current) return;
			current.delete(handler);
			if (current.size === 0) {
				this.topics.delete(topic);
				this.send({ type: 'unsubscribe', topic });
			}
		};
	}

	close(): void {
		this.stopped = true;
		if (this.timer) clearTimeout(this.timer);
		this.stopPing();
		if (this.socket) {
			this.socket.onclose = null;
			this.socket.onmessage = null;
			this.socket.close();
		}
		this.socket = null;
	}

	private send(message: object): void {
		if (this.socket?.readyState === OPEN) {
			this.socket.send(JSON.stringify(message));
		}
	}

	private ensureOpen(): void {
		if (this.socket || this.stopped) return;
		const socket = this.create(this.url);
		this.socket = socket;
		socket.onopen = () => {
			this.delay = 1000;
			for (const topic of this.topics.keys()) {
				socket.send(JSON.stringify({ type: 'subscribe', topic }));
			}
			this.stopPing();
			this.pinger = setInterval(() => this.send({ type: 'ping' }), PING_INTERVAL);
		};
		socket.onmessage = (event) => this.dispatch(event.data);
		socket.onclose = (event) => {
			this.socket = null;
			this.stopPing();
			if (event.code === SESSION_ENDED) {
				this.stopped = true;
				this.onSessionEnd();
				return;
			}
			if (this.stopped || this.topics.size === 0) return;
			const wait = this.delay + Math.random() * 1000;
			this.delay = Math.min(this.delay * 2, MAX_DELAY);
			this.timer = setTimeout(() => {
				this.timer = null;
				this.ensureOpen();
			}, wait);
		};
	}

	private stopPing(): void {
		if (this.pinger) clearInterval(this.pinger);
		this.pinger = null;
	}

	private dispatch(raw: unknown): void {
		if (typeof raw !== 'string') return;
		let message: ServerMessage;
		try {
			message = JSON.parse(raw);
		} catch {
			return;
		}
		if (typeof message !== 'object' || message === null) return;
		const topic = 'topic' in message ? message.topic : undefined;
		if (typeof topic !== 'string') return;
		if (message.type === 'room_changed') {
			this.send({ type: 'subscribe', topic });
		}
		for (const handler of this.topics.get(topic) ?? []) {
			handler(message);
		}
	}
}
```

`frontend/src/lib/live/merge.ts`:

```ts
import type { LivePC, PublicSeat } from '$lib/api/types';
import type { ServerMessage } from './types';

export function seatKey(row: number, col: number): string {
	return `${row}:${col}`;
}

export function adminRoomReducer(current: Map<number, LivePC>, message: ServerMessage): Map<number, LivePC> {
	if (message.type === 'snapshot' && 'pcs' in message) {
		return new Map(message.pcs.map((pc) => [pc.id, pc]));
	}
	if (message.type === 'pc') {
		return new Map(current).set(message.pc.id, message.pc);
	}
	return current;
}

export function publicRoomReducer(
	current: Map<string, PublicSeat>,
	message: ServerMessage
): Map<string, PublicSeat> {
	if (message.type === 'snapshot' && 'seats' in message) {
		return new Map(message.seats.map((seat) => [seatKey(seat.row, seat.col), seat]));
	}
	if (message.type === 'seat') {
		return new Map(current).set(seatKey(message.seat.row, message.seat.col), message.seat);
	}
	return current;
}
```

`frontend/src/lib/live/index.ts`:

```ts
import { goto, invalidateAll } from '$app/navigation';
import { LiveSocket } from './socket';

let shared: LiveSocket | null = null;

export function live(): LiveSocket {
	if (!shared) {
		const scheme = location.protocol === 'https:' ? 'wss' : 'ws';
		shared = new LiveSocket(`${scheme}://${location.host}/ws/live`, undefined, async () => {
			shared = null;
			// 레이아웃의 me를 다시 읽어야 관리자 메뉴가 사라진다
			await invalidateAll();
			await goto('/login');
		});
	}
	return shared;
}

export function resetLive(): void {
	shared?.close();
	shared = null;
}
```

`frontend/src/lib/grid.ts`:

```ts
export type Cell =
	| { kind: 'seat'; row: number; col: number; number: number }
	| { kind: 'aisle'; key: string };

export function gridCells(rows: number, cols: number, aisleAfter: number | null): Cell[] {
	const cells: Cell[] = [];
	for (let row = 0; row < rows; row++) {
		for (let col = 0; col < cols; col++) {
			cells.push({ kind: 'seat', row, col, number: row * cols + col + 1 });
			if (aisleAfter && col + 1 === aisleAfter) {
				cells.push({ kind: 'aisle', key: `aisle-${row}` });
			}
		}
	}
	return cells;
}

export function gridColumns(cols: number, aisleAfter: number | null): string {
	if (aisleAfter) {
		return `repeat(${aisleAfter}, minmax(0, 1fr)) 24px repeat(${cols - aisleAfter}, minmax(0, 1fr))`;
	}
	return `repeat(${cols}, minmax(0, 1fr))`;
}
```

`frontend/src/lib/pcState.ts`:

```ts
import type { LivePC } from '$lib/api/types';

export type PcStateKey = 'offline' | 'no_user' | 'locked' | 'active';

const LABELS: Record<PcStateKey, string> = {
	offline: '오프라인',
	no_user: '로그인 없음',
	locked: '잠금',
	active: '사용 중'
};

export function pcState(pc: Pick<LivePC, 'online' | 'session'>): { key: PcStateKey; label: string } {
	let key: PcStateKey = 'offline';
	if (pc.online) {
		key = pc.session === 'active' ? 'active' : pc.session === 'locked' ? 'locked' : 'no_user';
	}
	return { key, label: LABELS[key] };
}
```

- [ ] **Step 4: 테스트와 타입 검사**

Run: `pnpm test && pnpm check`
Expected: 모두 통과, 0/0

- [ ] **Step 5: Commit**

```bash
git add frontend
git commit -m "feat(frontend): live socket with topic refcounting, reducers and seat grid math"
```

---

### Task 4: 앱 틀, 로그인, 등록 링크

**Files:**
- Modify: `frontend/src/routes/+layout.ts`, `frontend/src/routes/+layout.svelte`
- Create: `frontend/src/routes/login/+page.svelte`, `frontend/src/routes/enroll/[token]/+page.ts`, `frontend/src/routes/enroll/[token]/+page.svelte`, `frontend/src/routes/settings/+layout.ts`, `frontend/src/lib/components/ConfirmButton.svelte`

**Interfaces:**
- Consumes: `api`, `errorMessage`, `fieldErrors`, `safeNext`, `resetLive`, `Me`, `EnrollInfo`
- Produces:
  - 루트 레이아웃 데이터 `{ me: Me }` (`/api/auth/me` 호출로 CSRF 쿠키도 받음). 사이드바: 누구나 "실습실", 관리자만 "실습실 관리", "PC", "등록 PIN", "관리자 계정", "기록". 하단에 로그인/로그아웃
  - `/settings/*`는 비로그인이면 `/login?next=...`로
  - `/login`: 비밀번호 → 인증 코드 두 단계. 성공하면 `resetLive()`, `invalidateAll()`, `safeNext(next)`로 이동. `totp_not_enrolled`는 안내 문구, `no_pending_login`이면 비밀번호 단계로
  - `/enroll/[token]`: QR, 직접 입력용 secret, (새 계정이면) 비밀번호 두 번, 인증 코드 → 완료 안내와 로그인 링크
  - `ConfirmButton` props: `label: string`, `message: string`, `confirmLabel?: string`, `danger?: boolean`, `small?: boolean`, `disabled?: boolean`, `onconfirm: () => void | Promise<void>` (`<dialog>`로 확인받은 뒤 실행)

- [ ] **Step 1: 루트 레이아웃과 설정 가드**

`frontend/src/routes/+layout.ts`:

```ts
import { api } from '$lib/api/client';
import type { Me } from '$lib/api/types';
import type { LayoutLoad } from './$types';

export const ssr = false;
export const prerender = false;

const ANONYMOUS: Me = { authenticated: false, user: null };

export const load: LayoutLoad = async () => {
	const { data } = await api.GET('/api/auth/me');
	return { me: data ?? ANONYMOUS };
};
```

`frontend/src/routes/+layout.svelte`:

```svelte
<script lang="ts">
	import '../app.css';
	import type { Snippet } from 'svelte';
	import { goto, invalidateAll } from '$app/navigation';
	import { page } from '$app/state';
	import { api } from '$lib/api/client';
	import { resetLive } from '$lib/live';
	import type { LayoutData } from './$types';

	let { data, children }: { data: LayoutData; children: Snippet } = $props();

	const links = [
		{ href: '/', label: '실습실', admin: false, prefix: '/rooms' },
		{ href: '/settings/rooms', label: '실습실 관리', admin: true, prefix: '/settings/rooms' },
		{ href: '/settings/pcs', label: 'PC', admin: true, prefix: '/settings/pcs' },
		{ href: '/settings/pins', label: '등록 PIN', admin: true, prefix: '/settings/pins' },
		{ href: '/settings/admins', label: '관리자 계정', admin: true, prefix: '/settings/admins' },
		{ href: '/settings/audit', label: '기록', admin: true, prefix: '/settings/audit' }
	];

	const visible = $derived(links.filter((link) => !link.admin || data.me.authenticated));

	function active(prefix: string): boolean {
		return page.url.pathname === '/' ? prefix === '/rooms' : page.url.pathname.startsWith(prefix);
	}

	async function logout() {
		// 서버는 로그아웃할 때 열린 소켓을 4401로 닫는다. 먼저 끊어야 세션 종료 처리(/login 이동)가 돌지 않는다
		resetLive();
		await api.POST('/api/auth/logout');
		await invalidateAll();
		await goto('/');
	}
</script>

<div class="flex min-h-screen flex-wrap">
	<nav aria-label="주 메뉴" class="flex flex-[1_1_220px] flex-col gap-1 bg-side px-3.5 py-5">
		<div class="flex items-baseline gap-2 px-3 pt-1 pb-5">
			<span class="text-lg font-bold tracking-wide text-white">WCMS</span>
			<span class="text-xs text-side-muted">2026.1</span>
		</div>
		{#each visible as link (link.href)}
			<a
				href={link.href}
				aria-current={active(link.prefix) ? 'page' : undefined}
				class="flex min-h-11 items-center rounded-lg px-3 text-side-ink no-underline hover:bg-side-hover hover:text-white {active(
					link.prefix
				)
					? 'bg-side-on font-semibold text-white'
					: ''}"
			>
				{link.label}
			</a>
		{/each}
		<div class="flex-1"></div>
		<div class="flex items-center justify-between gap-2 border-t border-side-on px-3 pt-3 text-[13px] text-side-ink">
			{#if data.me.authenticated && data.me.user}
				<span>{data.me.user.username}</span>
				<button type="button" class="cursor-pointer text-side-muted underline" onclick={logout}>로그아웃</button>
			{:else}
				<a href="/login" class="text-side-muted">관리자 로그인</a>
			{/if}
		</div>
	</nav>
	<main class="flex min-w-0 flex-[999_1_560px] flex-col gap-5 px-8 pt-7 pb-10">
		{@render children()}
	</main>
</div>
```

`frontend/src/routes/settings/+layout.ts`:

```ts
import { redirect } from '@sveltejs/kit';
import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ parent, url }) => {
	const { me } = await parent();
	if (!me.authenticated) {
		redirect(307, `/login?next=${encodeURIComponent(url.pathname + url.search)}`);
	}
};
```

- [ ] **Step 2: 로그인 화면**

`frontend/src/routes/login/+page.svelte`:

```svelte
<script lang="ts">
	import { goto, invalidateAll } from '$app/navigation';
	import { page } from '$app/state';
	import { api } from '$lib/api/client';
	import { errorMessage } from '$lib/api/errors';
	import { resetLive } from '$lib/live';
	import { safeNext } from '$lib/nav';

	let step = $state<'password' | 'otp'>('password');
	let username = $state('');
	let password = $state('');
	let code = $state('');
	let error = $state('');
	let busy = $state(false);

	async function submitPassword(event: SubmitEvent) {
		event.preventDefault();
		busy = true;
		error = '';
		const { error: failure } = await api.POST('/api/auth/login', { body: { username, password } });
		busy = false;
		password = '';
		if (failure) {
			error = errorMessage(failure);
			return;
		}
		step = 'otp';
	}

	async function submitCode(event: SubmitEvent) {
		event.preventDefault();
		busy = true;
		error = '';
		const { error: failure } = await api.POST('/api/auth/otp', { body: { code } });
		busy = false;
		code = '';
		if (failure) {
			error = errorMessage(failure);
			if ((failure as { error?: string }).error === 'no_pending_login') {
				step = 'password';
			}
			return;
		}
		resetLive();
		await invalidateAll();
		await goto(safeNext(page.url.searchParams.get('next')));
	}
</script>

<section class="card flex w-full max-w-[420px] flex-col gap-3">
	<h1 class="page-title">관리자 로그인</h1>
	{#if error}<p class="error-box" role="alert">{error}</p>{/if}
	{#if step === 'password'}
		<form class="flex flex-col gap-2.5" onsubmit={submitPassword}>
			<label class="label" for="username">아이디</label>
			<input id="username" class="field" autocomplete="username" required bind:value={username} />
			<label class="label" for="password">비밀번호</label>
			<input
				id="password"
				class="field"
				type="password"
				autocomplete="current-password"
				required
				bind:value={password}
			/>
			<button class="btn btn-primary" type="submit" disabled={busy}>다음</button>
		</form>
	{:else}
		<form class="flex flex-col gap-2.5" onsubmit={submitCode}>
			<label class="label" for="code">인증 앱의 6자리 코드</label>
			<input
				id="code"
				class="field"
				inputmode="numeric"
				autocomplete="one-time-code"
				maxlength="7"
				required
				bind:value={code}
			/>
			<button class="btn btn-primary" type="submit" disabled={busy}>로그인</button>
		</form>
	{/if}
</section>
```

- [ ] **Step 3: 등록 링크 화면**

`frontend/src/routes/enroll/[token]/+page.ts`:

```ts
import { api } from '$lib/api/client';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params }) => {
	const { data } = await api.GET('/api/auth/enroll/{token}', { params: { path: { token: params.token } } });
	return { token: params.token, info: data ?? null };
};
```

`frontend/src/routes/enroll/[token]/+page.svelte`:

```svelte
<script lang="ts">
	import { api } from '$lib/api/client';
	import { errorMessage, fieldErrors } from '$lib/api/errors';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	let password = $state('');
	let confirm = $state('');
	let code = $state('');
	let error = $state('');
	let fields = $state<Record<string, string>>({});
	let done = $state(false);
	let busy = $state(false);

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		error = '';
		fields = {};
		if (data.info?.needs_password && password !== confirm) {
			fields = { password: '두 비밀번호가 다릅니다.' };
			return;
		}
		busy = true;
		const body = data.info?.needs_password ? { password, code } : { code };
		const { error: failure } = await api.POST('/api/auth/enroll/{token}', {
			params: { path: { token: data.token } },
			body
		});
		busy = false;
		if (failure) {
			error = errorMessage(failure);
			fields = fieldErrors(failure);
			return;
		}
		done = true;
	}
</script>

<section class="card flex w-full max-w-[460px] flex-col gap-3">
	<h1 class="page-title">계정 등록</h1>
	{#if !data.info}
		<p class="error-box">링크가 만료됐거나 이미 사용됐습니다. 관리자에게 새 링크를 받으세요.</p>
	{:else if done}
		<p class="notice-box">등록이 끝났습니다.</p>
		<a class="btn btn-primary" href="/login">로그인하러 가기</a>
	{:else}
		<p class="meta">
			{data.info.username} 계정입니다. 인증 앱(Google Authenticator 등)으로 QR 코드를 찍고, 앱에 나온 6자리 코드를
			입력하세요.
		</p>
		<!-- 서버가 만든 QR SVG다. 사용자 입력이 텍스트로 들어가지 않는다. -->
		<div class="self-start">{@html data.info.qr_svg}</div>
		<p class="meta">직접 입력: <span class="font-mono">{data.info.secret}</span></p>
		{#if error}<p class="error-box" role="alert">{error}</p>{/if}
		<form class="flex flex-col gap-2.5" onsubmit={submit}>
			{#if data.info.needs_password}
				<label class="label" for="password">비밀번호 (10자 이상)</label>
				<input id="password" class="field" type="password" autocomplete="new-password" required bind:value={password} />
				<label class="label" for="confirm">비밀번호 확인</label>
				<input id="confirm" class="field" type="password" autocomplete="new-password" required bind:value={confirm} />
				{#if fields.password}<p class="text-[13px] text-danger">{fields.password}</p>{/if}
			{/if}
			<label class="label" for="code">6자리 코드</label>
			<input id="code" class="field" inputmode="numeric" maxlength="7" required bind:value={code} />
			<button class="btn btn-primary" type="submit" disabled={busy}>등록</button>
		</form>
	{/if}
</section>
```

- [ ] **Step 4: 확인 버튼 컴포넌트**

`frontend/src/lib/components/ConfirmButton.svelte`:

```svelte
<script lang="ts">
	let {
		label,
		message,
		confirmLabel = label,
		danger = false,
		small = false,
		disabled = false,
		onconfirm
	}: {
		label: string;
		message: string;
		confirmLabel?: string;
		danger?: boolean;
		small?: boolean;
		disabled?: boolean;
		onconfirm: () => void | Promise<void>;
	} = $props();

	let dialog: HTMLDialogElement | undefined = $state();
	let busy = $state(false);

	async function confirmAction() {
		busy = true;
		await onconfirm();
		busy = false;
		dialog?.close();
	}
</script>

<button
	type="button"
	class="btn {danger ? 'btn-danger' : ''} {small ? 'btn-sm' : ''}"
	{disabled}
	onclick={() => dialog?.showModal()}
>
	{label}
</button>

<dialog bind:this={dialog} class="m-auto w-[min(420px,calc(100%-32px))] rounded-[14px] p-0 backdrop:bg-black/40">
	<div class="flex flex-col gap-4 p-5">
		<p>{message}</p>
		<div class="flex justify-end gap-2">
			<button type="button" class="btn" onclick={() => dialog?.close()}>취소</button>
			<button
				type="button"
				class="btn {danger ? 'btn-danger' : 'btn-primary'}"
				disabled={busy}
				onclick={confirmAction}
			>
				{confirmLabel}
			</button>
		</div>
	</div>
</dialog>
```

- [ ] **Step 5: 확인**

Run: `pnpm check && pnpm test && pnpm build`
Expected: 0/0, 테스트 통과, 빌드 성공

- [ ] **Step 6: Commit**

```bash
git add frontend
git commit -m "feat(frontend): app shell, two-step login, enrollment page, confirm dialog"
```

---

### Task 5: 실습실 실시간 그리드

**Files:**
- Create: `frontend/src/lib/components/SeatGrid.svelte`, `frontend/src/lib/components/AdminTile.svelte`, `frontend/src/lib/components/PublicTile.svelte`
- Modify: `frontend/src/routes/+page.svelte`
- Create: `frontend/src/routes/+page.ts`, `frontend/src/routes/rooms/[id]/+page.ts`, `frontend/src/routes/rooms/[id]/+page.svelte`

**Interfaces:**
- Consumes: `live()`, `adminRoomReducer`, `publicRoomReducer`, `seatKey`, `gridCells`, `gridColumns`, `pcState`, `/api/public/rooms`, `/api/public/rooms/{id}`
- Produces:
  - `/`: 첫 실습실로 이동, 없으면 안내
  - `/rooms/[id]`: 실습실 탭, 온라인 수/전체, 좌석 격자. 관리자는 `room:<id>` 구독(라벨, 상태, 사용자, 앞 창), 비로그인은 `room:<id>:public` 구독(라벨, 켜짐/꺼짐만)
  - `SeatGrid` props: `rows`, `cols`, `aisleAfter`, `seat: Snippet<[Extract<Cell, { kind: 'seat' }>]>`
  - `AdminTile` props: `pc: LivePC`. `PublicTile` props: `seat: PublicSeat`

- [ ] **Step 1: 컴포넌트**

`frontend/src/lib/components/SeatGrid.svelte`:

```svelte
<script lang="ts">
	import type { Snippet } from 'svelte';
	import { gridCells, gridColumns, type Cell } from '$lib/grid';

	type SeatCell = Extract<Cell, { kind: 'seat' }>;

	let {
		rows,
		cols,
		aisleAfter,
		seat
	}: { rows: number; cols: number; aisleAfter: number | null; seat: Snippet<[SeatCell]> } = $props();

	const cells = $derived(gridCells(rows, cols, aisleAfter));
	const columns = $derived(gridColumns(cols, aisleAfter));
</script>

<div class="overflow-x-auto">
	<div class="grid min-w-[960px] gap-3" style:grid-template-columns={columns}>
		{#each cells as cell (cell.kind === 'seat' ? `${cell.row}:${cell.col}` : cell.key)}
			{#if cell.kind === 'aisle'}
				<div aria-hidden="true"></div>
			{:else}
				{@render seat(cell)}
			{/if}
		{/each}
	</div>
</div>
```

`frontend/src/lib/components/AdminTile.svelte`:

```svelte
<script lang="ts">
	import type { LivePC } from '$lib/api/types';
	import { pcState } from '$lib/pcState';

	let { pc }: { pc: LivePC } = $props();

	const display = $derived(pcState(pc));
	const screen: Record<string, string> = {
		offline: 'bg-[#2a2d34] text-[#a9afbb]',
		no_user: 'bg-[#3b4a5a] text-white',
		locked: 'bg-[#4a3f2a] text-white',
		active: 'bg-[#2f5c7a] text-white'
	};
	const foreground = $derived(
		pc.foreground ? [pc.foreground.process, pc.foreground.title].filter(Boolean).join(' · ') : ''
	);
</script>

<article class="flex min-h-[120px] flex-col overflow-hidden rounded-[10px] border border-line bg-surface" data-pc-id={pc.id}>
	<div class="flex aspect-[16/10] items-center justify-center text-xs {screen[display.key]}">{display.label}</div>
	<div class="flex items-center justify-between gap-1.5 px-2.5 py-2">
		<span class="text-[13px] font-semibold">{pc.label}</span>
		<span class="text-xs {display.key === 'active' ? 'font-semibold text-ok' : 'text-muted'}">{display.label}</span>
	</div>
	<div class="flex flex-col gap-0.5 px-2.5 pb-2 text-xs text-muted">
		<span class="truncate">{pc.user}</span>
		<span class="truncate">{foreground}</span>
	</div>
</article>
```

`frontend/src/lib/components/PublicTile.svelte`:

```svelte
<script lang="ts">
	import type { PublicSeat } from '$lib/api/types';

	let { seat }: { seat: PublicSeat } = $props();
</script>

<article class="flex min-h-[72px] flex-col justify-between rounded-[10px] border border-line bg-surface px-3 py-2.5">
	<span class="text-[13px] font-semibold">{seat.label}</span>
	<span class="inline-flex items-center gap-1.5 text-xs {seat.online ? 'font-semibold text-ok' : 'text-muted'}">
		<span class="size-2 rounded-full {seat.online ? 'bg-ok' : 'bg-[#a3a8b2]'}"></span>
		{seat.online ? '켜짐' : '꺼짐'}
	</span>
</article>
```

- [ ] **Step 2: 홈과 실습실 화면**

`frontend/src/routes/+page.ts`:

```ts
import { redirect } from '@sveltejs/kit';
import { api } from '$lib/api/client';
import type { PageLoad } from './$types';

export const load: PageLoad = async () => {
	const { data } = await api.GET('/api/public/rooms');
	const rooms = data ?? [];
	if (rooms.length > 0) {
		redirect(307, `/rooms/${rooms[0].id}`);
	}
	return {};
};
```

`frontend/src/routes/+page.svelte`:

```svelte
<section class="card flex max-w-[420px] flex-col gap-2">
	<h1 class="page-title">실습실</h1>
	<p class="meta">등록된 실습실이 없습니다. 관리자가 실습실 관리에서 추가해야 합니다.</p>
</section>
```

`frontend/src/routes/rooms/[id]/+page.ts`:

```ts
import { error } from '@sveltejs/kit';
import { api } from '$lib/api/client';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params }) => {
	const id = Number(params.id);
	const [detail, rooms] = await Promise.all([
		api.GET('/api/public/rooms/{id}', { params: { path: { id } } }),
		api.GET('/api/public/rooms')
	]);
	if (!detail.data) {
		error(404, '없는 실습실입니다.');
	}
	return { room: detail.data.room, rooms: rooms.data ?? [] };
};
```

`frontend/src/routes/rooms/[id]/+page.svelte`:

```svelte
<script lang="ts">
	import AdminTile from '$lib/components/AdminTile.svelte';
	import PublicTile from '$lib/components/PublicTile.svelte';
	import SeatGrid from '$lib/components/SeatGrid.svelte';
	import { invalidateAll } from '$app/navigation';
	import type { LivePC, PublicSeat } from '$lib/api/types';
	import { live } from '$lib/live';
	import { adminRoomReducer, publicRoomReducer, seatKey } from '$lib/live/merge';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const admin = $derived(data.me.authenticated);
	const topic = $derived(admin ? `room:${data.room.id}` : `room:${data.room.id}:public`);

	let pcs = $state(new Map<number, LivePC>());
	let seats = $state(new Map<string, PublicSeat>());
	let problem = $state('');

	$effect(() => {
		const current = topic;
		const isAdmin = admin;
		pcs = new Map();
		seats = new Map();
		problem = '';
		return live().subscribe(current, (message) => {
			if (message.type === 'room_changed') {
				// 크기, 이름, 통로가 바뀌었거나 지워졌을 수 있다. 좌석은 LiveSocket이 다시 구독해 받는다
				void invalidateAll();
				return;
			}
			if (message.type === 'error') {
				if (message.error === 'forbidden_topic') {
					// 서버 재시작 등으로 로그인이 풀렸다. me를 다시 읽으면 비로그인 토픽으로 바뀐다
					void invalidateAll();
					return;
				}
				problem = '실시간 정보를 불러오지 못했습니다.';
				return;
			}
			if (isAdmin) {
				pcs = adminRoomReducer(pcs, message);
			} else {
				seats = publicRoomReducer(seats, message);
			}
		});
	});

	const pcBySeat = $derived(
		new Map(
			[...pcs.values()]
				.filter((pc) => pc.row !== null && pc.col !== null)
				.map((pc) => [seatKey(pc.row as number, pc.col as number), pc])
		)
	);
	const onlineCount = $derived(
		admin ? [...pcs.values()].filter((pc) => pc.online).length : [...seats.values()].filter((s) => s.online).length
	);
	const total = $derived(admin ? pcs.size : seats.size);
</script>

<header class="flex flex-wrap items-end justify-between gap-4">
	<div>
		<h1 class="page-title">실습실 {data.room.name}</h1>
		<p class="meta">온라인 {onlineCount} / {total}</p>
	</div>
</header>

<nav aria-label="실습실" class="flex flex-wrap gap-1.5 self-start rounded-[10px] bg-[#e9ecf1] p-1">
	{#each data.rooms as room (room.id)}
		<a
			href="/rooms/{room.id}"
			aria-current={room.id === data.room.id ? 'page' : undefined}
			class="inline-flex min-h-10 items-center rounded-lg border px-4 font-medium no-underline {room.id === data.room.id
				? 'border-[#d5d9e0] bg-surface font-semibold text-ink'
				: 'border-transparent text-[#3d424d] hover:bg-[#dde1e8]'}"
		>
			{room.name}
		</a>
	{/each}
</nav>

{#if problem}<p class="error-box" role="alert">{problem}</p>{/if}

<section class="card" aria-label="좌석 배치">
	<div class="mb-4 flex justify-center">
		<span class="rounded-md border border-dashed border-[#c4c9d2] px-10 py-1 text-xs text-muted">교탁</span>
	</div>
	<SeatGrid rows={data.room.rows} cols={data.room.cols} aisleAfter={data.room.aisle_after}>
		{#snippet seat(cell)}
			{@const key = seatKey(cell.row, cell.col)}
			{#if admin && pcBySeat.get(key)}
				<AdminTile pc={pcBySeat.get(key)!} />
			{:else if !admin && seats.get(key)}
				<PublicTile seat={seats.get(key)!} />
			{:else}
				<div class="flex min-h-[72px] items-center justify-center rounded-[10px] border border-dashed border-line text-xs text-muted">
					{cell.number}
				</div>
			{/if}
		{/snippet}
	</SeatGrid>
</section>
```

- [ ] **Step 3: 확인**

Run: `pnpm check && pnpm test && pnpm build`
Expected: 0/0, 통과, 빌드 성공

- [ ] **Step 4: Commit**

```bash
git add frontend
git commit -m "feat(frontend): live room seat grid for admins and anonymous viewers"
```

---

### Task 6: 실습실 관리와 좌석 배치

**Files:**
- Create: `frontend/src/routes/settings/rooms/+page.ts`, `+page.svelte`, `frontend/src/routes/settings/rooms/[id]/+page.ts`, `+page.svelte`

**Interfaces:**
- Consumes: `/api/rooms`, `/api/rooms/{id}`, `/api/rooms/{id}/seats`, `/api/pcs`, `SeatGrid`, `ConfirmButton`, `errorMessage`, `fieldErrors`
- Produces:
  - `/settings/rooms`: 실습실 목록(이름, 크기, 자리 배치 링크), 추가 폼(이름, 줄, 열, 통로 위치(비우면 없음), 정렬 순서) → 추가 후 그 실습실 편집 화면으로
  - `/settings/rooms/[id]`: 크기 수정(PATCH), 좌석마다 PC 선택(비움 + 전체 PC 목록, 다른 실습실에 앉은 PC는 이름 옆에 현재 자리 표시) → 저장(PUT seats), 실습실 삭제(확인 창)

- [ ] **Step 1: 목록과 추가**

`frontend/src/routes/settings/rooms/+page.ts`:

```ts
import { api } from '$lib/api/client';
import type { PageLoad } from './$types';

export const load: PageLoad = async () => {
	const { data } = await api.GET('/api/rooms');
	return { rooms: data ?? [] };
};
```

`frontend/src/routes/settings/rooms/+page.svelte`:

```svelte
<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api/client';
	import { errorMessage, fieldErrors } from '$lib/api/errors';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	let name = $state('');
	let rows = $state(5);
	let cols = $state(8);
	let aisle = $state<number | null>(4);
	let sortOrder = $state(0);
	let error = $state('');
	let fields = $state<Record<string, string>>({});

	async function create(event: SubmitEvent) {
		event.preventDefault();
		error = '';
		fields = {};
		const { data: room, error: failure } = await api.POST('/api/rooms', {
			body: { name, rows, cols, aisle_after: aisle || null, sort_order: sortOrder }
		});
		if (failure || !room) {
			error = errorMessage(failure);
			fields = fieldErrors(failure);
			return;
		}
		await goto(`/settings/rooms/${room.id}`);
	}
</script>

<h1 class="page-title">실습실 관리</h1>

<section class="card">
	<h2 class="mb-3 text-base font-semibold">실습실</h2>
	{#if data.rooms.length === 0}
		<p class="meta">아직 없습니다.</p>
	{:else}
		<table class="w-full border-collapse">
			<thead>
				<tr class="text-left text-xs text-muted">
					<th class="px-3 py-2.5">이름</th>
					<th class="px-3 py-2.5">크기</th>
					<th class="px-3 py-2.5"><span class="sr-only">편집</span></th>
				</tr>
			</thead>
			<tbody>
				{#each data.rooms as room (room.id)}
					<tr class="border-t border-line-soft">
						<td class="px-3 py-2.5">{room.name}</td>
						<td class="px-3 py-2.5">{room.rows} × {room.cols}</td>
						<td class="px-3 py-2.5 text-right"><a href="/settings/rooms/{room.id}">자리 배치</a></td>
					</tr>
				{/each}
			</tbody>
		</table>
	{/if}
</section>

<section class="card max-w-[480px]">
	<h2 class="mb-3 text-base font-semibold">실습실 추가</h2>
	{#if error}<p class="error-box mb-3" role="alert">{error}</p>{/if}
	<form class="flex flex-col gap-2.5" onsubmit={create}>
		<label class="label" for="name">이름</label>
		<input id="name" class="field" required bind:value={name} />
		{#if fields.name}<p class="text-[13px] text-danger">{fields.name}</p>{/if}
		<div class="flex gap-3">
			<div class="flex flex-1 flex-col gap-1.5">
				<label class="label" for="rows">줄 수</label>
				<input id="rows" class="field" type="number" min="1" max="20" required bind:value={rows} />
			</div>
			<div class="flex flex-1 flex-col gap-1.5">
				<label class="label" for="cols">열 수</label>
				<input id="cols" class="field" type="number" min="1" max="20" required bind:value={cols} />
			</div>
		</div>
		<label class="label" for="aisle">통로 위치 (N번째 열 뒤, 비우면 없음)</label>
		<input id="aisle" class="field" type="number" min="1" bind:value={aisle} />
		{#if fields.aisle_after}<p class="text-[13px] text-danger">{fields.aisle_after}</p>{/if}
		<label class="label" for="sort">정렬 순서</label>
		<input id="sort" class="field" type="number" min="0" bind:value={sortOrder} />
		<button class="btn btn-primary" type="submit">추가</button>
	</form>
</section>
```

- [ ] **Step 2: 크기 수정, 좌석 배치, 삭제**

`frontend/src/routes/settings/rooms/[id]/+page.ts`:

```ts
import { error } from '@sveltejs/kit';
import { api } from '$lib/api/client';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params }) => {
	const id = Number(params.id);
	const path = { params: { path: { id } } };
	const [room, seats, pcs] = await Promise.all([
		api.GET('/api/rooms/{id}', path),
		api.GET('/api/rooms/{id}/seats', path),
		api.GET('/api/pcs')
	]);
	if (!room.data || !seats.data) {
		error(404, '없는 실습실입니다.');
	}
	return { room: room.data, seats: seats.data.seats, pcs: pcs.data ?? [] };
};
```

`frontend/src/routes/settings/rooms/[id]/+page.svelte`:

```svelte
<script lang="ts">
	import { goto, invalidateAll } from '$app/navigation';
	import { api } from '$lib/api/client';
	import { errorMessage, fieldErrors } from '$lib/api/errors';
	import ConfirmButton from '$lib/components/ConfirmButton.svelte';
	import SeatGrid from '$lib/components/SeatGrid.svelte';
	import { seatKey } from '$lib/live/merge';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	let name = $state('');
	let rows = $state(1);
	let cols = $state(1);
	let aisle = $state<number | null>(null);
	let assignment = $state<Record<string, number | ''>>({});
	let error = $state('');
	let fields = $state<Record<string, string>>({});
	let saved = $state('');

	$effect.pre(() => {
		name = data.room.name;
		rows = data.room.rows;
		cols = data.room.cols;
		aisle = data.room.aisle_after ?? null;
		assignment = Object.fromEntries(data.seats.map((s) => [seatKey(s.row, s.col), s.pc]));
	});

	function pcText(pc: PageData['pcs'][number]): string {
		return pc.room !== null && pc.room !== data.room.id ? `${pc.hostname} (${pc.label})` : pc.hostname;
	}

	async function saveSize(event: SubmitEvent) {
		event.preventDefault();
		error = '';
		fields = {};
		const { error: failure } = await api.PATCH('/api/rooms/{id}', {
			params: { path: { id: data.room.id } },
			body: { name, rows, cols, aisle_after: aisle || null }
		});
		if (failure) {
			error = errorMessage(failure);
			fields = fieldErrors(failure);
			return;
		}
		saved = '저장했습니다.';
		await invalidateAll();
	}

	async function saveSeats() {
		error = '';
		saved = '';
		// 아직 고르지 않은 자리는 undefined, "비움"을 고른 자리는 ''
		const seats = Object.entries(assignment)
			.filter(([, pc]) => pc !== '' && pc !== undefined)
			.map(([key, pc]) => {
				const [row, col] = key.split(':').map(Number);
				return { row, col, pc: pc as number };
			});
		const { error: failure } = await api.PUT('/api/rooms/{id}/seats', {
			params: { path: { id: data.room.id } },
			body: { seats }
		});
		if (failure) {
			error = [errorMessage(failure), ...Object.values(fieldErrors(failure))].join(' ');
			return;
		}
		saved = '좌석 배치를 저장했습니다.';
		await invalidateAll();
	}

	async function remove() {
		const { error: failure } = await api.DELETE('/api/rooms/{id}', { params: { path: { id: data.room.id } } });
		if (failure) {
			error = errorMessage(failure);
			return;
		}
		await goto('/settings/rooms');
	}
</script>

<header class="flex flex-wrap items-end justify-between gap-4">
	<div>
		<h1 class="page-title">{data.room.name} 자리 배치</h1>
		<p class="meta"><a href="/settings/rooms">실습실 관리</a></p>
	</div>
	<ConfirmButton
		label="실습실 삭제"
		message="{data.room.name} 실습실을 삭제합니다. 앉아 있던 PC는 모두 자리 미배정이 됩니다."
		danger
		onconfirm={remove}
	/>
</header>

{#if error}<p class="error-box" role="alert">{error}</p>{/if}
{#if saved}<p class="notice-box" role="status">{saved}</p>{/if}

<section class="card">
	<h2 class="mb-3 text-base font-semibold">크기</h2>
	<form class="flex flex-wrap items-end gap-4" onsubmit={saveSize}>
		<div class="flex flex-col gap-1.5">
			<label class="label" for="name">이름</label>
			<input id="name" class="field" required bind:value={name} />
		</div>
		<div class="flex w-24 flex-col gap-1.5">
			<label class="label" for="rows">줄 수</label>
			<input id="rows" class="field" type="number" min="1" max="20" bind:value={rows} />
		</div>
		<div class="flex w-24 flex-col gap-1.5">
			<label class="label" for="cols">열 수</label>
			<input id="cols" class="field" type="number" min="1" max="20" bind:value={cols} />
		</div>
		<div class="flex w-40 flex-col gap-1.5">
			<label class="label" for="aisle">통로 (N열 뒤)</label>
			<input id="aisle" class="field" type="number" min="1" bind:value={aisle} />
		</div>
		<button class="btn" type="submit">크기 저장</button>
	</form>
	{#each Object.entries(fields) as [field, message] (field)}
		<p class="mt-2 text-[13px] text-danger">{message}</p>
	{/each}
</section>

<section class="card">
	<div class="mb-3 flex items-center justify-between">
		<h2 class="text-base font-semibold">자리</h2>
		<button class="btn btn-primary" type="button" onclick={saveSeats}>좌석 배치 저장</button>
	</div>
	<SeatGrid rows={data.room.rows} cols={data.room.cols} aisleAfter={data.room.aisle_after ?? null}>
		{#snippet seat(cell)}
			{@const key = seatKey(cell.row, cell.col)}
			<div class="flex min-w-0 flex-col gap-1">
				<label class="text-xs text-muted" for="seat-{key}">{cell.number}</label>
				<select id="seat-{key}" class="field w-full" bind:value={assignment[key]}>
					<option value="">비움</option>
					{#each data.pcs as pc (pc.id)}
						<option value={pc.id}>{pcText(pc)}</option>
					{/each}
				</select>
			</div>
		{/snippet}
	</SeatGrid>
</section>
```

- [ ] **Step 3: 확인**

Run: `pnpm check && pnpm build`
Expected: 0/0, 빌드 성공

- [ ] **Step 4: Commit**

```bash
git add frontend
git commit -m "feat(frontend): room management and seat assignment"
```

---

### Task 7: PC, 등록 PIN, 관리자 계정, 기록 화면

**Files:**
- Create: `frontend/src/routes/settings/pcs/+page.ts`, `+page.svelte`, `frontend/src/routes/settings/pins/+page.ts`, `+page.svelte`, `frontend/src/routes/settings/admins/+page.ts`, `+page.svelte`, `frontend/src/routes/settings/audit/+page.svelte`

**Interfaces:**
- Consumes: `/api/pcs`, `/api/pcs/{id}`, `/api/pins`, `/api/pins/{id}`, `/api/admins`, `/api/admins/{id}`, `/api/admins/{id}/reset`, `/api/audit`, `ConfirmButton`, `formatTime`
- Produces:
  - `/settings/pcs`: 호스트 이름, 자리, 버전, 등록 시각, 삭제(확인 창)
  - `/settings/pins`: 새 PIN 만들기(여러 대 사용, 10분/1시간/3시간), 새 PIN 크게 표시, 사용 가능한 PIN 목록, 폐기(확인 창)
  - `/settings/admins`: 목록(인증 앱 등록 여부, 나), 추가 → 등록 링크(전체 URL) 표시 + 복사 버튼, 인증 앱 재설정(확인 창) → 링크, 삭제(확인 창, 나는 비활성)
  - `/settings/audit`: 최신순 50개, "더 보기"로 다음 페이지 (`next`의 `cursor` 값 사용)

- [ ] **Step 1: PC 화면**

`frontend/src/routes/settings/pcs/+page.ts`:

```ts
import { api } from '$lib/api/client';
import type { PageLoad } from './$types';

export const load: PageLoad = async () => {
	const { data } = await api.GET('/api/pcs');
	return { pcs: data ?? [] };
};
```

`frontend/src/routes/settings/pcs/+page.svelte`:

```svelte
<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { api } from '$lib/api/client';
	import { errorMessage } from '$lib/api/errors';
	import ConfirmButton from '$lib/components/ConfirmButton.svelte';
	import { formatTime } from '$lib/format';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
	let error = $state('');

	async function remove(id: number) {
		const { error: failure } = await api.DELETE('/api/pcs/{id}', { params: { path: { id } } });
		error = failure ? errorMessage(failure) : '';
		await invalidateAll();
	}
</script>

<h1 class="page-title">PC</h1>
{#if error}<p class="error-box" role="alert">{error}</p>{/if}

<section class="card overflow-x-auto">
	{#if data.pcs.length === 0}
		<p class="meta">등록된 PC가 없습니다.</p>
	{:else}
		<table class="w-full min-w-[640px] border-collapse">
			<thead>
				<tr class="text-left text-xs text-muted">
					<th class="px-3 py-2.5">호스트 이름</th>
					<th class="px-3 py-2.5">자리</th>
					<th class="px-3 py-2.5">버전</th>
					<th class="px-3 py-2.5">등록</th>
					<th class="px-3 py-2.5"><span class="sr-only">삭제</span></th>
				</tr>
			</thead>
			<tbody>
				{#each data.pcs as pc (pc.id)}
					<tr class="border-t border-line-soft">
						<td class="px-3 py-2.5 font-semibold">{pc.hostname}</td>
						<td class="px-3 py-2.5">{pc.room !== null ? pc.label : '미배정'}</td>
						<td class="px-3 py-2.5 font-mono">{pc.client_version}</td>
						<td class="px-3 py-2.5 text-muted">{formatTime(pc.registered_at)}</td>
						<td class="px-3 py-2.5 text-right">
							<ConfirmButton
								label="삭제"
								message="{pc.hostname}을(를) 삭제합니다. 이 PC의 클라이언트는 연결이 끊기고 다시 등록해야 합니다."
								danger
								small
								onconfirm={() => remove(pc.id)}
							/>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{/if}
</section>
```

- [ ] **Step 2: 등록 PIN 화면**

`frontend/src/routes/settings/pins/+page.ts`:

```ts
import { api } from '$lib/api/client';
import type { PageLoad } from './$types';

export const load: PageLoad = async () => {
	const { data } = await api.GET('/api/pins');
	return { pins: data ?? [] };
};
```

`frontend/src/routes/settings/pins/+page.svelte`:

```svelte
<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { api } from '$lib/api/client';
	import { errorMessage } from '$lib/api/errors';
	import type { Pin } from '$lib/api/types';
	import ConfirmButton from '$lib/components/ConfirmButton.svelte';
	import { formatTime } from '$lib/format';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	let multiUse = $state(true);
	let minutes = $state<10 | 60 | 180>(60);
	let created = $state<Pin | null>(null);
	let error = $state('');

	async function create(event: SubmitEvent) {
		event.preventDefault();
		const { data: pin, error: failure } = await api.POST('/api/pins', { body: { multi_use: multiUse, minutes } });
		if (failure || !pin) {
			error = errorMessage(failure);
			return;
		}
		error = '';
		created = pin;
		await invalidateAll();
	}

	async function revoke(id: number) {
		await api.DELETE('/api/pins/{id}', { params: { path: { id } } });
		if (created?.id === id) created = null;
		await invalidateAll();
	}
</script>

<h1 class="page-title">등록 PIN</h1>
{#if error}<p class="error-box" role="alert">{error}</p>{/if}
{#if created}
	<p class="notice-box" role="status">
		새 PIN <strong class="font-mono text-lg">{created.pin}</strong> · {formatTime(created.expires_at)}까지{created.multi_use
			? ' · 여러 대 사용 가능'
			: ''}
	</p>
{/if}

<section class="card max-w-[420px]">
	<h2 class="mb-3 text-base font-semibold">PIN 만들기</h2>
	<form class="flex flex-col gap-2.5" onsubmit={create}>
		<label class="label" for="minutes">유효 시간</label>
		<select id="minutes" class="field" bind:value={minutes}>
			<option value={10}>10분</option>
			<option value={60}>1시간</option>
			<option value={180}>3시간</option>
		</select>
		<label class="flex min-h-11 items-center gap-2"><input type="checkbox" bind:checked={multiUse} /> 여러 대에 사용</label>
		<button class="btn btn-primary" type="submit">만들기</button>
	</form>
</section>

<section class="card">
	<h2 class="mb-3 text-base font-semibold">사용 가능한 PIN</h2>
	{#if data.pins.length === 0}
		<p class="meta">없습니다.</p>
	{:else}
		<table class="w-full border-collapse">
			<thead>
				<tr class="text-left text-xs text-muted">
					<th class="px-3 py-2.5">PIN</th>
					<th class="px-3 py-2.5">만료</th>
					<th class="px-3 py-2.5">방식</th>
					<th class="px-3 py-2.5">사용</th>
					<th class="px-3 py-2.5"><span class="sr-only">폐기</span></th>
				</tr>
			</thead>
			<tbody>
				{#each data.pins as pin (pin.id)}
					<tr class="border-t border-line-soft">
						<td class="px-3 py-2.5 font-mono">{pin.pin}</td>
						<td class="px-3 py-2.5">{formatTime(pin.expires_at)}</td>
						<td class="px-3 py-2.5">{pin.multi_use ? '여러 대' : '1회'}</td>
						<td class="px-3 py-2.5">{pin.used_count}</td>
						<td class="px-3 py-2.5 text-right">
							<ConfirmButton
								label="폐기"
								message="PIN {pin.pin}을(를) 폐기합니다. 이 PIN으로는 더 이상 등록할 수 없습니다."
								danger
								small
								onconfirm={() => revoke(pin.id)}
							/>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{/if}
</section>
```

- [ ] **Step 3: 관리자 계정 화면**

`frontend/src/routes/settings/admins/+page.ts`:

```ts
import { api } from '$lib/api/client';
import type { PageLoad } from './$types';

export const load: PageLoad = async () => {
	const { data } = await api.GET('/api/admins');
	return { admins: data ?? [] };
};
```

`frontend/src/routes/settings/admins/+page.svelte`:

```svelte
<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { api } from '$lib/api/client';
	import { errorMessage, fieldErrors } from '$lib/api/errors';
	import ConfirmButton from '$lib/components/ConfirmButton.svelte';
	import { formatTime } from '$lib/format';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	let username = $state('');
	let link = $state<{ who: string; url: string; expires: string } | null>(null);
	let copied = $state(false);
	let error = $state('');
	let fields = $state<Record<string, string>>({});

	function showLink(who: string, enrollUrl: string, expiresAt: string) {
		link = { who, url: `${location.origin}${enrollUrl}`, expires: formatTime(expiresAt) };
		copied = false;
	}

	async function create(event: SubmitEvent) {
		event.preventDefault();
		error = '';
		fields = {};
		const { data: result, error: failure } = await api.POST('/api/admins', { body: { username } });
		if (failure || !result) {
			error = errorMessage(failure);
			fields = fieldErrors(failure);
			return;
		}
		showLink(result.admin.username, result.enroll_url, result.expires_at);
		username = '';
		await invalidateAll();
	}

	async function reset(id: number, who: string) {
		const { data: result, error: failure } = await api.POST('/api/admins/{id}/reset', { params: { path: { id } } });
		if (failure || !result) {
			error = errorMessage(failure);
			return;
		}
		showLink(who, result.enroll_url, result.expires_at);
		await invalidateAll();
	}

	async function remove(id: number) {
		const { error: failure } = await api.DELETE('/api/admins/{id}', { params: { path: { id } } });
		error = failure ? errorMessage(failure) : '';
		await invalidateAll();
	}

	async function copy() {
		if (link) {
			await navigator.clipboard.writeText(link.url);
			copied = true;
		}
	}
</script>

<h1 class="page-title">관리자 계정</h1>
{#if error}<p class="error-box" role="alert">{error}</p>{/if}

{#if link}
	<section class="notice-box flex flex-col gap-2" role="status">
		<p>{link.who}에게 아래 등록 링크를 전달하세요. {link.expires}까지 한 번만 쓸 수 있습니다.</p>
		<div class="flex flex-wrap items-center gap-2">
			<code class="min-w-0 flex-1 break-all rounded bg-surface px-2 py-1.5 font-mono text-ink">{link.url}</code>
			<button class="btn btn-sm" type="button" onclick={copy}>{copied ? '복사됨' : '복사'}</button>
		</div>
	</section>
{/if}

<section class="card overflow-x-auto">
	<table class="w-full min-w-[560px] border-collapse">
		<thead>
			<tr class="text-left text-xs text-muted">
				<th class="px-3 py-2.5">아이디</th>
				<th class="px-3 py-2.5">인증 앱</th>
				<th class="px-3 py-2.5"><span class="sr-only">관리</span></th>
			</tr>
		</thead>
		<tbody>
			{#each data.admins as admin (admin.id)}
				<tr class="border-t border-line-soft">
					<td class="px-3 py-2.5 font-semibold">{admin.username}{admin.is_self ? ' (나)' : ''}</td>
					<td class="px-3 py-2.5">{admin.totp_enrolled ? '등록됨' : '등록 대기'}</td>
					<td class="flex justify-end gap-2 px-3 py-2.5">
						<ConfirmButton
							label="인증 앱 재설정"
							message="{admin.username}의 인증 앱 재설정 링크를 만듭니다. 이전에 만든 링크는 무효가 됩니다."
							small
							onconfirm={() => reset(admin.id, admin.username)}
						/>
						<ConfirmButton
							label="삭제"
							message="{admin.username} 계정을 삭제합니다."
							danger
							small
							disabled={admin.is_self}
							onconfirm={() => remove(admin.id)}
						/>
					</td>
				</tr>
			{/each}
		</tbody>
	</table>
</section>

<section class="card max-w-[420px]">
	<h2 class="mb-3 text-base font-semibold">관리자 추가</h2>
	<form class="flex flex-col gap-2.5" onsubmit={create}>
		<label class="label" for="username">아이디</label>
		<input id="username" class="field" required bind:value={username} />
		{#if fields.username}<p class="text-[13px] text-danger">{fields.username}</p>{/if}
		<button class="btn btn-primary" type="submit">추가하고 등록 링크 만들기</button>
	</form>
</section>
```

- [ ] **Step 4: 기록 화면**

`frontend/src/routes/settings/audit/+page.svelte`:

```svelte
<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api/client';
	import type { AuditLog } from '$lib/api/types';
	import { formatTime } from '$lib/format';

	let entries = $state<AuditLog[]>([]);
	let cursor = $state<string | null>(null);
	let loading = $state(false);

	function cursorOf(next: string | null | undefined): string | null {
		return next ? new URL(next, location.origin).searchParams.get('cursor') : null;
	}

	async function load(from: string | null) {
		loading = true;
		const { data } = await api.GET('/api/audit', { params: { query: from ? { cursor: from } : {} } });
		loading = false;
		if (data) {
			entries = [...entries, ...data.results];
			cursor = cursorOf(data.next);
		}
	}

	onMount(() => {
		void load(null);
	});
</script>

<h1 class="page-title">기록</h1>

<section class="card overflow-x-auto">
	<table class="w-full min-w-[640px] border-collapse">
		<thead>
			<tr class="text-left text-xs text-muted">
				<th class="px-3 py-2.5">시각</th>
				<th class="px-3 py-2.5">관리자</th>
				<th class="px-3 py-2.5">동작</th>
				<th class="px-3 py-2.5">대상</th>
			</tr>
		</thead>
		<tbody>
			{#each entries as entry (entry.id)}
				<tr class="border-t border-line-soft">
					<td class="px-3 py-2.5 text-muted">{formatTime(entry.created_at)}</td>
					<td class="px-3 py-2.5">{entry.actor ?? '-'}</td>
					<td class="px-3 py-2.5 font-mono">{entry.action}</td>
					<td class="px-3 py-2.5 font-mono">{entry.target}</td>
				</tr>
			{/each}
		</tbody>
	</table>
	{#if cursor}
		<div class="mt-3 flex justify-center">
			<button class="btn btn-sm" type="button" disabled={loading} onclick={() => load(cursor)}>더 보기</button>
		</div>
	{/if}
</section>
```

- [ ] **Step 5: 확인**

Run: `pnpm check && pnpm test && pnpm build`
Expected: 0/0, 통과, 빌드 성공

- [ ] **Step 6: Commit**

```bash
git add frontend
git commit -m "feat(frontend): PC, registration PIN, admin account and audit screens"
```

---

### Task 8: 실제 서버로 확인, 문서

**Files:**
- Modify: `README.md`, `CLAUDE.md`

**Interfaces:**
- Consumes: 계획 02 서버, `server/tools/fake_client.py`

- [ ] **Step 1: 타입이 최신인지 확인**

Run: `pnpm gen:api && git diff --exit-code src/lib/api/schema.d.ts`
Expected: 차이 없음

- [ ] **Step 2: 서버와 화면 띄우기 (임시 DB)**

```bash
cd server
export WCMS_DB_PATH="$(mktemp -d)/wcms.sqlite3"
uv run python manage.py migrate
uv run python manage.py createadmin admin
uv run uvicorn wcms.asgi:application --port 8000
```

다른 터미널: `cd frontend && pnpm dev`

- [ ] **Step 3: 브라우저로 확인 (수동, 또는 컨트롤러가 내장 브라우저로)**

1. `http://localhost:5173` → "등록된 실습실이 없습니다"
2. createadmin이 출력한 `/enroll/...`를 `http://localhost:5173/enroll/...`로 열기 → QR과 secret 보임. 비밀번호 두 번 + 인증 코드(secret으로 `uv run python -c "import pyotp; print(pyotp.TOTP('<secret>').now())"`) → "등록이 끝났습니다"
3. `/login` → 비밀번호 → 인증 코드(다음 30초 구간 코드) → 사이드바에 관리자 메뉴
4. 실습실 관리 → 301 (5×8, 통로 4) 추가 → 자리 배치 화면
5. 등록 PIN → 여러 대, 1시간 → 새 PIN 표시
6. `cd server && uv run python tools/fake_client.py --pin <PIN> --count 3` → PC 화면에 FAKE-01~03
7. 자리 배치에서 FAKE-01~03을 1~3번 자리에 → 저장 → 실습실 화면에서 세 칸이 실시간으로 사용자·앞 창을 바꿔 보여줌 (새로고침 없이)
8. 시크릿 창으로 `/rooms/<id>` → 라벨과 켜짐/꺼짐만, 호스트 이름·사용자·앞 창 없음
9. 가짜 클라이언트 종료 → 두 창 모두 꺼짐/오프라인으로 바뀜
10. 관리자 계정 → 추가 → 링크 복사 버튼 동작, 재설정·삭제는 확인 창을 거침, 내 계정 삭제 버튼은 비활성
11. 로그아웃 → 관리자 메뉴 사라짐, 실습실 화면은 비로그인 표시로
12. 기록 → 위 동작들이 최신순으로 보임

문제가 있으면 해당 Task 파일을 고치고 그 Task의 확인 단계를 다시 돈다.

- [ ] **Step 4: 정리**

서버·개발 서버를 끄고, 임시 DB와 `server/tools/.fake_clients.json`을 지운다.

- [ ] **Step 5: README와 CLAUDE.md**

`README.md`의 "## 서버 실행 (개발)" 섹션 아래에 추가:

````markdown

## 화면 실행 (개발)

```bash
cd frontend
pnpm install
pnpm dev
```

`http://localhost:5173`. `/api`, `/ws`, `/client`는 `localhost:8000`의 서버로 넘긴다. 서버 API가 바뀌면 `pnpm gen:api`로 타입을 다시 만든다.

`localhost`가 아닌 주소(같은 망의 다른 PC 등)로 열려면 서버에 `WCMS_ALLOWED_HOSTS`와 `WCMS_CSRF_TRUSTED_ORIGINS`를 맞춰 준다. 개발 서버는 세션을 프로세스 메모리에 두므로 서버를 다시 켜면 다시 로그인해야 한다.

화면 테스트: `pnpm check && pnpm test`
````

`CLAUDE.md`의 `- frontend/: SvelteKit SPA (계획 03)` 줄을 아래로 바꾼다.

```markdown
- frontend/: SvelteKit SPA. 명령은 frontend/ 에서 pnpm. API 타입은 `pnpm gen:api`로 생성 (손으로 쓰지 않음). `{@html}` 금지 (등록 QR만 예외)
```

- [ ] **Step 6: Commit**

```bash
git add README.md CLAUDE.md
git commit -m "docs: frontend run instructions"
```

---

## 실행 결과 및 다음 계획으로 넘기는 항목

계획 03은 완료됐다 (화면 테스트 56개 통과, `pnpm check` 경고 없음). Task 8의 12단계 확인은 실제 서버와 내장 브라우저로 모두 통과했다. 실행 중 계획과 달라진 점:

- `pnpm add`는 호환 메이저를 고정한다 (SvelteKit 2, adapter-static 3, Svelte 5, TypeScript 5, Tailwind 4).
- 로드 함수는 타입이 넓어지는 곳에서 `satisfies LayoutLoad/PageLoad`를 쓴다.
- `safeNext`는 고정 origin에 대해 해석해 같은 origin일 때만 따른다 (`//`, `/\`, 탭·줄바꿈 우회 차단).
- 자리 배치의 빈 자리는 `''`로 채워 저장 뒤에도 "비움"이 보인다.
- 클라이언트 미들웨어(`src/lib/api/middleware.ts`, 테스트 있음): CSRF, 401 이동, 연결 실패(fetch 거부)와 본문이 오류 형식이 아닌 실패 응답(프록시의 빈 502 등)을 `{error, detail}`로 바꿔 모든 화면이 기존 오류 분기를 탄다.
- `ConfirmButton`은 `onconfirm`이 실패해도 busy를 푼다. 실습실을 줄여 자리 배정이 풀리면 몇 대인지 묻는다.
- LiveSocket: 연결 상태(`connecting/open/closed`) 노출, ping 뒤 10초 안에 아무 메시지가 없으면 끊고 재접속, 안정적으로 열린 뒤에만 backoff 초기화, 핸들러 예외 격리. 실습실 화면은 연결이 끊긴 동안 안내를 띄운다.
- 세션 종료 시 `/login?next=<현재 경로>`로 간다. 로그아웃 요청이 실패하면 오류를 보이고 화면을 다시 구독한다.
- 실습실 로드가 연결 실패면 "없는 실습실"이 아니라 오류로 보인다.

### 계획 04에서 처리

- 실시간 상태를 `src/lib/live`의 토픽별 store로 옮기고 마지막 스냅샷을 보관한다 (같은 토픽의 두 번째 구독자도 바로 받음). PC 상세, 선택, 우클릭 메뉴가 같은 상태를 쓴다
- ping에 대한 4401이 10초보다 늦으면 감시 타이머가 먼저 끊어 세션 종료 대신 재접속한다 (`forbidden_topic`으로 회복은 됨)
- 세션 종료·로그아웃 순간 "다시 연결하는 중" 안내가 잠깐 보임
- `ConfirmButton`에 대상 대수 표시(설계 3.9)와 `onconfirm` 오류 표시
- 401 때 `next`가 이동 대상이 아니라 현재 화면을 가리킴, hover 미리 불러오기 중 401이면 로그인으로 이동
- 인증 코드 단계에서 비밀번호 단계로 돌아가기, 등록 링크 실패를 모두 "만료"로 보이는 문제, QR 접근성 이름
- `forbidden_topic`인데 여전히 로그인 상태면 안내 없음, 상세 로드 실패의 구분
- 자리 배치·크기 저장이 저장 안 한 다른 쪽 편집을 덮어씀, 크기 칸을 비우면 줄임 확인의 대수가 틀림, 실습실 추가 폼의 줄·열 오류 표시, 자리 배정 변환을 lib로 빼서 테스트
- 관리자 화면: `<td>`의 flex, 성공 뒤 남는 오류, 삭제한 관리자의 링크 상자
- 기록 화면의 동작 코드(`admin.delete`, `user:2`)를 한국어로, 삭제된 관리자 이름 (서버 `actor_name`과 함께)
- 로그아웃 실패 시 다시 그리기가 설정 화면의 입력도 지움, `+error.svelte` 없음
- LiveSocket 테스트 보강 (늦은 close 테스트가 약함)

### 계획 06에서 처리

- 바이너리 프레임: `binaryType = 'arraybuffer'`와 바이너리 분배 경로 (지금은 문자열이 아니면 버림)
- 실습실 전환 때 한 프레임 동안 이전 실습실 상태가 보임 (`{#key}`), 관리자 칸의 상태 글자 중복, 좁은 폭에서 칸 글자 줄바꿈

### 계획 09에서 처리

- 글꼴을 직접 제공 (지금은 Google Fonts), favicon, 버전을 `VERSION`에서 주입, `Referrer-Policy`, Node 버전 고정, CI에서 `pnpm gen:api` 차이 검사
