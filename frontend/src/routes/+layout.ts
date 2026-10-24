import { api } from '$lib/api/client';
import type { Me } from '$lib/api/types';
import type { LayoutLoad } from './$types';

export const ssr = false;
export const prerender = false;

const ANONYMOUS: Me = { authenticated: false, user: null };

export const load = (async () => {
	const { data } = await api.GET('/api/auth/me');
	return { me: data ?? ANONYMOUS };
}) satisfies LayoutLoad;
