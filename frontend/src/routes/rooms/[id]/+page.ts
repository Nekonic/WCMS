import { error } from '@sveltejs/kit';
import { api } from '$lib/api/client';
import { errorMessage } from '$lib/api/errors';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ params }) => {
	const id = Number(params.id);
	const [detail, rooms] = await Promise.all([
		api.GET('/api/public/rooms/{id}', { params: { path: { id } } }),
		api.GET('/api/public/rooms')
	]);
	if (!detail.data) {
		// 서버에 연결하지 못한 것(503)까지 없는 실습실로 보이지 않게 한다
		if (detail.response.status >= 400 && detail.response.status !== 404) error(detail.response.status, errorMessage(detail.error));
		error(404, '없는 실습실입니다.');
	}
	return { room: detail.data.room, rooms: rooms.data ?? [] };
};
