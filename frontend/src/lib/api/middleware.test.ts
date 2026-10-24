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
		const result = await middleware.onResponse!({
			request: new Request(`${ORIGIN}/api/rooms`),
			response,
			...params
		});
		expect(result).toBe(response);
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
});
