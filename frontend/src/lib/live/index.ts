import { goto, invalidateAll } from '$app/navigation';
import { LiveSocket } from './socket';

let shared: LiveSocket | null = null;

export function live(): LiveSocket {
	if (!shared) {
		const scheme = location.protocol === 'https:' ? 'wss' : 'ws';
		shared = new LiveSocket(`${scheme}://${location.host}/ws/live`, undefined, async () => {
			shared = null;
			// 레이아웃의 me를 다시 읽어야 관리자 메뉴가 사라진다
			await invalidateAll();
			await goto('/login');
		});
	}
	return shared;
}

export function resetLive(): void {
	shared?.close();
	shared = null;
}
