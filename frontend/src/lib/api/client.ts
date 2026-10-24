import createClient from 'openapi-fetch';
import { goto } from '$app/navigation';
import { createMiddleware } from './middleware';
import type { paths } from './schema';

export const api = createClient<paths>({ baseUrl: location.origin });
api.use(
	createMiddleware({
		cookie: () => document.cookie,
		location: () => location,
		navigate: (url) => goto(url)
	})
);
