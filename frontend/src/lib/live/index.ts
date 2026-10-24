import { goto, invalidateAll } from '$app/navigation';
import { loginUrl } from '$lib/api/middleware';
import { LiveSocket } from './socket';

export type { LiveStatus } from './socket';

let shared: LiveSocket | null = null;

export function live(): LiveSocket {
	if (!shared) {
		const scheme = location.protocol === 'https:' ? 'wss' : 'ws';
		const instance: LiveSocket = new LiveSocket(`${scheme}://${location.host}/ws/live`, undefined, async () => {
			// 그 사이 resetLive()로 새 연결이 생겼으면 그것은 그대로 둔다
			if (shared === instance) shared = null;
			const next = loginUrl(location.pathname, location.search);
			// 레이아웃의 me를 다시 읽어야 관리자 메뉴가 사라진다
			await invalidateAll();
			await goto(next);
		});
		shared = instance;
	}
	return shared;
}

export function resetLive(): void {
	shared?.close();
	shared = null;
}
