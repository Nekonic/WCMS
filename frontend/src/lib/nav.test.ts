import { describe, expect, it } from 'vitest';
import { safeNext } from './nav';

describe('safeNext', () => {
	it('keeps local paths', () => {
		expect(safeNext('/settings/pins?x=1')).toBe('/settings/pins?x=1');
	});
	it('rejects external or missing targets', () => {
		for (const value of [null, '', 'https://evil.example', '//evil.example', '/\\evil.example', '/\t/evil.example', '/\n/evil.example', '/\r/evil.example', 'settings']) {
			expect(safeNext(value)).toBe('/');
		}
	});
});
