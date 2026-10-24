import type { LivePC, PublicSeat } from '$lib/api/types';

export type ServerMessage =
	| { type: 'snapshot'; topic: string; pcs: LivePC[] }
	| { type: 'snapshot'; topic: string; seats: PublicSeat[] }
	| { type: 'snapshot'; topic: string; pc: LivePC }
	| { type: 'pc'; topic: string; pc: LivePC }
	| { type: 'seat'; topic: string; seat: PublicSeat }
	| { type: 'room_changed'; topic: string }
	| { type: 'error'; error: string; topic?: string }
	| { type: 'pong' };

export type Handler = (message: ServerMessage) => void;
