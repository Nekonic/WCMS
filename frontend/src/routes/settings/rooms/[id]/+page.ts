import { error } from '@sveltejs/kit';
import { api } from '$lib/api/client';
import { errorMessage } from '$lib/api/errors';
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
		// 서버에 연결하지 못한 것(503)까지 없는 실습실로 보이지 않게 한다
		const failed = room.data ? seats : room;
		if (failed.response.status >= 400 && failed.response.status !== 404) error(failed.response.status, errorMessage(failed.error));
		error(404, '없는 실습실입니다.');
	}
	return { room: room.data, seats: seats.data.seats, pcs: pcs.data ?? [] };
};
