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
