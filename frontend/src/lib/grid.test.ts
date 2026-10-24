import { describe, expect, it } from 'vitest';
import { gridCells, gridColumns } from './grid';

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
