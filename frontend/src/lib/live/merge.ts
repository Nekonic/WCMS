import type { LivePC, PublicSeat } from '$lib/api/types';
import type { ServerMessage } from './types';

export function seatKey(row: number, col: number): string {
	return `${row}:${col}`;
}

export function adminRoomReducer(current: Map<number, LivePC>, message: ServerMessage): Map<number, LivePC> {
	if (message.type === 'snapshot' && 'pcs' in message) {
		return new Map(message.pcs.map((pc) => [pc.id, pc]));
	}
	if (message.type === 'pc') {
		return new Map(current).set(message.pc.id, message.pc);
	}
	return current;
}

export function publicRoomReducer(
	current: Map<string, PublicSeat>,
	message: ServerMessage
): Map<string, PublicSeat> {
	if (message.type === 'snapshot' && 'seats' in message) {
		return new Map(message.seats.map((seat) => [seatKey(seat.row, seat.col), seat]));
	}
	if (message.type === 'seat') {
		return new Map(current).set(seatKey(message.seat.row, message.seat.col), message.seat);
	}
	return current;
}
