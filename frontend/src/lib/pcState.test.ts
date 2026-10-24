import { describe, expect, it } from 'vitest';
import type { LivePC } from '$lib/api/types';
import { pcState } from './pcState';

const make = (online: boolean, session: LivePC['session']) => ({ online, session }) as LivePC;

describe('pcState', () => {
	it('maps online and session to a display state', () => {
		expect(pcState(make(false, 'active'))).toEqual({ key: 'offline', label: '오프라인' });
		expect(pcState(make(true, 'none'))).toEqual({ key: 'no_user', label: '로그인 없음' });
		expect(pcState(make(true, 'locked'))).toEqual({ key: 'locked', label: '잠금' });
		expect(pcState(make(true, 'active'))).toEqual({ key: 'active', label: '사용 중' });
	});
});
