import type { Middleware } from 'openapi-fetch';
import { csrfToken } from './csrf';

const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS']);

export interface MiddlewareDeps {
	cookie: () => string;
	location: () => { origin: string; pathname: string; search: string };
	navigate: (url: string) => unknown;
}

export function loginUrl(pathname: string, search: string): string {
	return `/login?next=${encodeURIComponent(pathname + search)}`;
}

const NETWORK_BODY = { error: 'network', detail: '서버에 연결하지 못했습니다.' };
const SERVER_BODY = { error: 'server_error', detail: '서버가 요청을 처리하지 못했습니다.' };
// 프록시(Vite, nginx, Cloudflare)가 백엔드에 닿지 못했을 때 주는 상태
const GATEWAY_STATUSES = new Set([502, 503, 504]);

function jsonResponse(body: object, status: number): Response {
	return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

export function networkErrorResponse(): Response {
	return jsonResponse(NETWORK_BODY, 503);
}

async function hasErrorBody(response: Response): Promise<boolean> {
	try {
		const body: unknown = await response.clone().json();
		return typeof body === 'object' && body !== null && typeof (body as { error?: unknown }).error === 'string';
	} catch {
		return false;
	}
}

/**
 * 실패 응답의 본문이 서버의 오류 형식({error: string, ...})이 아니면 바꾼다.
 * 빈 본문이면 openapi-fetch가 error: ''를 돌려주고, 호출부의 if (failure)가 성공으로 지나간다
 */
async function normalizeError(response: Response): Promise<Response> {
	if (response.ok || response.status < 400 || (await hasErrorBody(response))) {
		return response;
	}
	return jsonResponse(GATEWAY_STATUSES.has(response.status) ? NETWORK_BODY : SERVER_BODY, response.status);
}

export function createMiddleware(deps: MiddlewareDeps): Middleware {
	return {
		onRequest({ request }) {
			if (!SAFE_METHODS.has(request.method)) {
				const token = csrfToken(deps.cookie());
				if (token) {
					request.headers.set('X-CSRFToken', token);
				}
			}
			return request;
		},
		async onResponse({ request, response }) {
			const here = deps.location();
			const path = new URL(request.url, here.origin).pathname;
			if (response.status === 401 && !path.startsWith('/api/auth/')) {
				await deps.navigate(loginUrl(here.pathname, here.search));
			}
			return normalizeError(response);
		},
		onError() {
			// fetch가 거부되면 (오프라인, 연결 끊김) openapi-fetch는 예외를 던진다. 호출부의 error 분기로 보내 busy가 풀리게 한다
			return networkErrorResponse();
		}
	};
}
