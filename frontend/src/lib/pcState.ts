import type { LivePC } from '$lib/api/types';

export type PcStateKey = 'offline' | 'no_user' | 'locked' | 'active';

const LABELS: Record<PcStateKey, string> = {
	offline: '오프라인',
	no_user: '로그인 없음',
	locked: '잠금',
	active: '사용 중'
};

export function pcState(pc: Pick<LivePC, 'online' | 'session'>): { key: PcStateKey; label: string } {
	let key: PcStateKey = 'offline';
	if (pc.online) {
		key = pc.session === 'active' ? 'active' : pc.session === 'locked' ? 'locked' : 'no_user';
	}
	return { key, label: LABELS[key] };
}
