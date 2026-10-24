import createClient from 'openapi-fetch';
import { describe, expect, it, vi } from 'vitest';
import { createMiddleware, loginUrl } from './middleware';

const ORIGIN = 'http://wcms.test';

function setup(cookie = 'csrftoken=tok%3D') {
	const navigate = vi.fn();
	const middleware = createMiddleware({
		cookie: () => cookie,
		location: () => ({ origin: ORIGIN, pathname: '/rooms/3', search: '?a=1&b=2' }),
		navigate
	});
	return { middleware, navigate };
}

const params = { schemaPath: '', params: {}, options: {} as never, id: 'x' };

describe('loginUrl', () => {
	it('encodes path and search into next', () => {
		expect(loginUrl('/rooms/3', '?a=1&b=2')).toBe('/login?next=%2Frooms%2F3%3Fa%3D1%26b%3D2');
	});
});

describe('api middleware', () => {
	it('adds X-CSRFToken on unsafe methods only', async () => {
		const { middleware } = setup();
		for (const method of ['POST', 'PUT', 'PATCH', 'DELETE']) {
			const request = new Request(`${ORIGIN}/api/rooms`, { method });
			const result = (await middleware.onRequest!({ request, ...params })) as Request;
			expect(result.headers.get('X-CSRFToken')).toBe('tok=');
		}
		for (const method of ['GET', 'HEAD', 'OPTIONS']) {
			const request = new Request(`${ORIGIN}/api/rooms`, { method });
			const result = (await middleware.onRequest!({ request, ...params })) as Request;
			expect(result.headers.get('X-CSRFToken')).toBeNull();
		}
	});

	it('reads the cookie at request time', async () => {
		let cookie = '';
		const middleware = createMiddleware({
			cookie: () => cookie,
			location: () => ({ origin: ORIGIN, pathname: '/', search: '' }),
			navigate: () => {}
		});
		const first = (await middleware.onRequest!({
			request: new Request(`${ORIGIN}/api/x`, { method: 'POST' }),
			...params
		})) as Request;
		expect(first.headers.get('X-CSRFToken')).toBeNull();
		cookie = 'csrftoken=new';
		const second = (await middleware.onRequest!({
			request: new Request(`${ORIGIN}/api/x`, { method: 'POST' }),
			...params
		})) as Request;
		expect(second.headers.get('X-CSRFToken')).toBe('new');
	});

	it('redirects to login on 401 outside /api/auth/', async () => {
		const { middleware, navigate } = setup();
		const response = new Response(null, { status: 401 });
		const result = (await middleware.onResponse!({
			request: new Request(`${ORIGIN}/api/rooms`),
			response,
			...params
		})) as Response;
		// 본문이 비었으므로 오류 형식으로 바뀐다 (상태는 그대로)
		expect(result.status).toBe(401);
		expect(await result.json()).toEqual({ error: 'server_error', detail: '서버가 요청을 처리하지 못했습니다.' });
		expect(navigate).toHaveBeenCalledWith('/login?next=%2Frooms%2F3%3Fa%3D1%26b%3D2');
	});

	it('does not redirect on 401 from /api/auth/', async () => {
		const { middleware, navigate } = setup();
		await middleware.onResponse!({
			request: new Request(`${ORIGIN}/api/auth/login`, { method: 'POST' }),
			response: new Response(null, { status: 401 }),
			...params
		});
		expect(navigate).not.toHaveBeenCalled();
	});

	it('does not redirect on other statuses', async () => {
		const { middleware, navigate } = setup();
		await middleware.onResponse!({
			request: new Request(`${ORIGIN}/api/rooms`),
			response: new Response(null, { status: 403 }),
			...params
		});
		expect(navigate).not.toHaveBeenCalled();
	});

	it('turns a network failure into a 503 error body', async () => {
		const { middleware } = setup();
		const result = await middleware.onError!({
			request: new Request(`${ORIGIN}/api/rooms`),
			error: new TypeError('Failed to fetch'),
			...params
		});
		expect(result).toBeInstanceOf(Response);
		const response = result as Response;
		expect(response.status).toBe(503);
		expect(response.headers.get('Content-Type')).toBe('application/json');
		expect(await response.json()).toEqual({ error: 'network', detail: '서버에 연결하지 못했습니다.' });
	});

	it('lets openapi-fetch callers take the error branch when fetch rejects', async () => {
		const { middleware } = setup();
		const client = createClient<Record<string, never>>({
			baseUrl: ORIGIN,
			fetch: () => Promise.reject(new TypeError('Failed to fetch'))
		});
		client.use(middleware);
		const result = await (client as unknown as { POST: (path: string) => Promise<{ error?: unknown }> }).POST(
			'/api/auth/logout'
		);
		expect(result.error).toEqual({ error: 'network', detail: '서버에 연결하지 못했습니다.' });
	});

	async function respond(response: Response, path = '/api/rooms') {
		const { middleware } = setup();
		return (await middleware.onResponse!({
			request: new Request(`${ORIGIN}${path}`, { method: 'POST' }),
			response,
			...params
		})) as Response;
	}

	it('turns an empty 502 into the network error body', async () => {
		const result = await respond(new Response('', { status: 502, headers: { 'Content-Type': 'text/plain' } }));
		expect(result.status).toBe(502);
		expect(result.headers.get('Content-Type')).toBe('application/json');
		expect(await result.json()).toEqual({ error: 'network', detail: '서버에 연결하지 못했습니다.' });
	});

	it('uses the network body for 503 and 504 without a JSON error', async () => {
		for (const status of [503, 504]) {
			const result = await respond(new Response('<html>down</html>', { status }));
			expect(result.status).toBe(status);
			expect(await result.json()).toEqual({ error: 'network', detail: '서버에 연결하지 못했습니다.' });
		}
	});

	it('turns an HTML 500 into server_error', async () => {
		const result = await respond(
			new Response('<html>oops</html>', { status: 500, headers: { 'Content-Type': 'text/html' } })
		);
		expect(result.status).toBe(500);
		expect(await result.json()).toEqual({ error: 'server_error', detail: '서버가 요청을 처리하지 못했습니다.' });
	});

	it('turns JSON without a string error field into server_error', async () => {
		for (const body of ['{"detail":"x"}', '[]', '"text"', '{"error":3}']) {
			const result = await respond(
				new Response(body, { status: 400, headers: { 'Content-Type': 'application/json' } })
			);
			expect(result.status).toBe(400);
			expect(await result.json()).toEqual({ error: 'server_error', detail: '서버가 요청을 처리하지 못했습니다.' });
		}
	});

	it('passes a proper JSON error body through unchanged', async () => {
		const original = new Response(JSON.stringify({ error: 'invalid', detail: '틀렸습니다.', fields: { a: ['b'] } }), {
			status: 400,
			headers: { 'Content-Type': 'application/json' }
		});
		const result = await respond(original);
		expect(result).toBe(original);
		expect(await result.json()).toEqual({ error: 'invalid', detail: '틀렸습니다.', fields: { a: ['b'] } });
	});

	it('leaves 2xx and 204 responses untouched', async () => {
		const ok = new Response('not json', { status: 200 });
		expect(await respond(ok)).toBe(ok);
		const empty = new Response(null, { status: 204 });
		expect(await respond(empty)).toBe(empty);
	});

	it('still redirects a 401 and keeps its JSON error', async () => {
		const { middleware, navigate } = setup();
		const original = new Response(JSON.stringify({ error: 'not_authenticated', detail: '로그인하세요.' }), {
			status: 401,
			headers: { 'Content-Type': 'application/json' }
		});
		const result = await middleware.onResponse!({
			request: new Request(`${ORIGIN}/api/rooms`),
			response: original,
			...params
		});
		expect(navigate).toHaveBeenCalledOnce();
		expect(result).toBe(original);
	});

	it('gives openapi-fetch callers a truthy error for an empty 502', async () => {
		const { middleware } = setup();
		const client = createClient<Record<string, never>>({
			baseUrl: ORIGIN,
			fetch: () => Promise.resolve(new Response('', { status: 502 }))
		});
		client.use(middleware);
		const result = await (client as unknown as { POST: (path: string) => Promise<{ error?: unknown }> }).POST(
			'/api/auth/login'
		);
		expect(result.error).toBeTruthy();
		expect(result.error).toEqual({ error: 'network', detail: '서버에 연결하지 못했습니다.' });
	});
});
