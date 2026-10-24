import { api } from '$lib/api/client';
import type { PageLoad } from './$types';

export const load: PageLoad = async () => {
	const { data } = await api.GET('/api/pcs');
	return { pcs: data ?? [] };
};
