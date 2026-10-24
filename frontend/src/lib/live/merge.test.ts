import { describe, expect, it } from 'vitest';
import type { LivePC, PublicSeat } from '$lib/api/types';
import { adminRoomReducer, publicRoomReducer, seatKey } from './merge';

const pc = (id: number, online: boolean): LivePC =>
	({ id, online, hostname: `H${id}`, label: `301-0${id}`, room: 1, row: 0, col: id - 1 }) as LivePC;
const seat = (col: number, online: boolean): PublicSeat => ({ row: 0, col, label: `301-0${col + 1}`, online });

describe('adminRoomReducer', () => {
	it('replaces state on snapshot and updates single pcs', () => {
		let state = adminRoomReducer(new Map(), { type: 'snapshot', topic: 'room:1', pcs: [pc(1, false), pc(2, false)] });
		expect(state.size).toBe(2);
		const before = state;
		state = adminRoomReducer(state, { type: 'pc', topic: 'room:1', pc: pc(2, true) });
		expect(state.get(2)?.online).toBe(true);
		expect(state).not.toBe(before);
	});
	it('ignores unrelated messages', () => {
		const state = new Map([[1, pc(1, true)]]);
		expect(adminRoomReducer(state, { type: 'room_changed', topic: 'room:1' })).toBe(state);
	});
});

describe('publicRoomReducer', () => {
	it('keys seats by position', () => {
		let state = publicRoomReducer(new Map(), { type: 'snapshot', topic: 'room:1:public', seats: [seat(0, false)] });
		state = publicRoomReducer(state, { type: 'seat', topic: 'room:1:public', seat: seat(0, true) });
		expect(state.get(seatKey(0, 0))?.online).toBe(true);
	});
});
