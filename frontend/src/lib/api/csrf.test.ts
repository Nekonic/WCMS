import { describe, expect, it } from 'vitest';
import { csrfToken } from './csrf';

describe('csrfToken', () => {
	it('reads the csrftoken cookie', () => {
		expect(csrfToken('a=1; csrftoken=abc%3D; b=2')).toBe('abc=');
	});
	it('returns null when missing', () => {
		expect(csrfToken('sessionid=x')).toBeNull();
		expect(csrfToken('')).toBeNull();
	});
});
