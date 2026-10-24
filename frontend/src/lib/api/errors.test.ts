import { describe, expect, it } from 'vitest';
import { errorMessage, fieldErrors } from './errors';

describe('errorMessage', () => {
	it('uses the server detail', () => {
		expect(errorMessage({ error: 'invalid_code', detail: '인증 코드가 올바르지 않습니다.' })).toBe(
			'인증 코드가 올바르지 않습니다.'
		);
	});
	it('falls back for unknown shapes', () => {
		expect(errorMessage(undefined)).toBe('요청을 처리하지 못했습니다.');
		expect(errorMessage('boom')).toBe('요청을 처리하지 못했습니다.');
	});
});

describe('fieldErrors', () => {
	it('flattens field error lists', () => {
		expect(
			fieldErrors({ error: 'invalid', detail: 'x', fields: { password: ['짧습니다.', '흔합니다.'], seats: 'x' } })
		).toEqual({ password: '짧습니다. 흔합니다.', seats: 'x' });
	});
	it('returns empty object without fields', () => {
		expect(fieldErrors({ error: 'x', detail: 'y' })).toEqual({});
	});
	it('uses a generic message for nested item errors', () => {
		expect(fieldErrors({ error: 'invalid', detail: 'x', fields: { seats: [{}, { pc: ['없는 PC'] }] } })).toEqual({
			seats: '입력값을 확인하세요.'
		});
	});
});
