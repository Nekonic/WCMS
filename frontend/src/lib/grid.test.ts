import { describe, expect, it } from 'vitest';
import { gridCells, gridColumns, seatsOutside } from './grid';

describe('gridCells', () => {
	it('numbers seats row by row and inserts aisles', () => {
		const cells = gridCells(2, 4, 2);
		expect(cells.filter((c) => c.kind === 'aisle')).toHaveLength(2);
		const seats = cells.filter((c) => c.kind === 'seat');
		expect(seats).toHaveLength(8);
		expect(seats[5]).toEqual({ kind: 'seat', row: 1, col: 1, number: 6 });
		expect(cells[2]).toEqual({ kind: 'aisle', key: 'aisle-0' });
	});
	it('has no aisle when aisleAfter is null', () => {
		expect(gridCells(1, 3, null).every((c) => c.kind === 'seat')).toBe(true);
	});
});

describe('gridColumns', () => {
	it('builds the template', () => {
		expect(gridColumns(8, 4)).toBe('repeat(4, minmax(0, 1fr)) 24px repeat(4, minmax(0, 1fr))');
		expect(gridColumns(5, null)).toBe('repeat(5, minmax(0, 1fr))');
	});
});

describe('seatsOutside', () => {
	const seats = [
		{ row: 0, col: 0 },
		{ row: 1, col: 2 },
		{ row: 2, col: 0 },
		{ row: 2, col: 2 }
	];
	it('counts seats past the new rows or cols (0-based)', () => {
		expect(seatsOutside(seats, 3, 3)).toBe(0);
		expect(seatsOutside(seats, 2, 3)).toBe(2);
		expect(seatsOutside(seats, 3, 2)).toBe(2);
		expect(seatsOutside(seats, 2, 2)).toBe(3);
		expect(seatsOutside(seats, 1, 1)).toBe(3);
	});
	it('is zero when growing or empty', () => {
		expect(seatsOutside(seats, 5, 5)).toBe(0);
		expect(seatsOutside([], 1, 1)).toBe(0);
	});
});
