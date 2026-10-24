import { api } from '$lib/api/client';
import type { PageLoad } from './$types';

export const load = (async ({ params }) => {
	const { data } = await api.GET('/api/auth/enroll/{token}', { params: { path: { token: params.token } } });
	return { token: params.token, info: data ?? null };
}) satisfies PageLoad;
