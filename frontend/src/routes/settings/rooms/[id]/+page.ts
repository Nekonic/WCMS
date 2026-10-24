import { error } from '@sveltejs/kit';
import { api } from '$lib/api/client';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params }) => {
	const id = Number(params.id);
	const path = { params: { path: { id } } };
	const [room, seats, pcs] = await Promise.all([
		api.GET('/api/rooms/{id}', path),
		api.GET('/api/rooms/{id}/seats', path),
		api.GET('/api/pcs')
	]);
	if (!room.data || !seats.data) {
		error(404, '없는 실습실입니다.');
	}
	return { room: room.data, seats: seats.data.seats, pcs: pcs.data ?? [] };
};
