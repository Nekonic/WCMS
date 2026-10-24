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

export function networkErrorResponse(): Response {
	return new Response(JSON.stringify({ error: 'network', detail: '서버에 연결하지 못했습니다.' }), {
		status: 503,
		headers: { 'Content-Type': 'application/json' }
	});
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
			return response;
		},
		onError() {
			// fetch가 거부되면 (오프라인, 연결 끊김) openapi-fetch는 예외를 던진다. 호출부의 error 분기로 보내 busy가 풀리게 한다
			return networkErrorResponse();
		}
	};
}
