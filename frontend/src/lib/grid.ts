export type Cell =
	| { kind: 'seat'; row: number; col: number; number: number }
	| { kind: 'aisle'; key: string };

export function gridCells(rows: number, cols: number, aisleAfter: number | null): Cell[] {
	const cells: Cell[] = [];
	for (let row = 0; row < rows; row++) {
		for (let col = 0; col < cols; col++) {
			cells.push({ kind: 'seat', row, col, number: row * cols + col + 1 });
			if (aisleAfter && col + 1 === aisleAfter) {
				cells.push({ kind: 'aisle', key: `aisle-${row}` });
			}
		}
	}
	return cells;
}

export function gridColumns(cols: number, aisleAfter: number | null): string {
	if (aisleAfter) {
		return `repeat(${aisleAfter}, minmax(0, 1fr)) 24px repeat(${cols - aisleAfter}, minmax(0, 1fr))`;
	}
	return `repeat(${cols}, minmax(0, 1fr))`;
}

/** 새 크기(rows × cols)로 줄이면 자리 배정이 풀리는 좌석 수. 행·열은 0부터 센다 */
export function seatsOutside(seats: { row: number; col: number }[], rows: number, cols: number): number {
	return seats.filter((seat) => seat.row >= rows || seat.col >= cols).length;
}
