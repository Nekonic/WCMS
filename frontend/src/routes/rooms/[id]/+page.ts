import { error } from '@sveltejs/kit';
import { api } from '$lib/api/client';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params }) => {
	const id = Number(params.id);
	const [detail, rooms] = await Promise.all([
		api.GET('/api/public/rooms/{id}', { params: { path: { id } } }),
		api.GET('/api/public/rooms')
	]);
	if (!detail.data) {
		error(404, '없는 실습실입니다.');
	}
	return { room: detail.data.room, rooms: rooms.data ?? [] };
};
