import { describe, expect, it } from 'vitest';
import { formatTime } from './format';

describe('formatTime', () => {
	it('shows Asia/Seoul time', () => {
		expect(formatTime('2026-10-25T06:04:00Z')).toContain('3:04');
	});
});
