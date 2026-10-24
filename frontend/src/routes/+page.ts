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
