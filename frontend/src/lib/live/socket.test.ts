import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { LiveSocket, SESSION_ENDED } from './socket';

class FakeSocket {
	readyState = 0;
	sent: unknown[] = [];
	onopen: ((ev: Event) => unknown) | null = null;
	onmessage: ((ev: MessageEvent) => unknown) | null = null;
	onclose: ((ev: CloseEvent) => unknown) | null = null;
	send(data: string) {
		this.sent.push(JSON.parse(data));
	}
	close() {}
	open() {
		this.readyState = 1;
		this.onopen?.(new Event('open'));
	}
	receive(message: object) {
		this.onmessage?.({ data: JSON.stringify(message) } as MessageEvent);
	}
	drop(code = 1006) {
		this.readyState = 3;
		this.onclose?.({ code } as CloseEvent);
	}
}

let sockets: FakeSocket[];
const create = () => {
	const socket = new FakeSocket();
	sockets.push(socket);
	return socket;
};

beforeEach(() => {
	sockets = [];
	vi.useFakeTimers();
});
afterEach(() => vi.useRealTimers());

describe('LiveSocket', () => {
	it('subscribes once per topic and unsubscribes after the last handler', () => {
		const live = new LiveSocket('ws://x/ws/live', create);
		const off1 = live.subscribe('room:1', () => {});
		const off2 = live.subscribe('room:1', () => {});
		sockets[0].open();
		expect(sockets[0].sent).toEqual([{ type: 'subscribe', topic: 'room:1' }]);
		off1();
		expect(sockets[0].sent).toHaveLength(1);
		off2();
		expect(sockets[0].sent).toEqual([
			{ type: 'subscribe', topic: 'room:1' },
			{ type: 'unsubscribe', topic: 'room:1' }
		]);
	});

	it('routes messages by topic', () => {
		const live = new LiveSocket('ws://x/ws/live', create);
		const a = vi.fn();
		const b = vi.fn();
		live.subscribe('room:1', a);
		live.subscribe('room:2', b);
		sockets[0].open();
		sockets[0].receive({ type: 'pc', topic: 'room:1', pc: { id: 1 } });
		expect(a).toHaveBeenCalledOnce();
		expect(b).not.toHaveBeenCalled();
	});

	it('reconnects with backoff and resubscribes', () => {
		const live = new LiveSocket('ws://x/ws/live', create);
		live.subscribe('room:1', () => {});
		sockets[0].open();
		sockets[0].drop();
		expect(sockets).toHaveLength(1);
		vi.advanceTimersByTime(2100);
		expect(sockets).toHaveLength(2);
		sockets[1].open();
		expect(sockets[1].sent).toEqual([{ type: 'subscribe', topic: 'room:1' }]);
	});

	it('resubscribes on room_changed', () => {
		const live = new LiveSocket('ws://x/ws/live', create);
		live.subscribe('room:1:public', () => {});
		sockets[0].open();
		sockets[0].receive({ type: 'room_changed', topic: 'room:1:public' });
		expect(sockets[0].sent).toEqual([
			{ type: 'subscribe', topic: 'room:1:public' },
			{ type: 'subscribe', topic: 'room:1:public' }
		]);
	});

	it('stops on session end', () => {
		const onEnd = vi.fn();
		const live = new LiveSocket('ws://x/ws/live', create, onEnd);
		live.subscribe('room:1', () => {});
		sockets[0].open();
		sockets[0].drop(SESSION_ENDED);
		vi.advanceTimersByTime(60_000);
		expect(onEnd).toHaveBeenCalledOnce();
		expect(sockets).toHaveLength(1);
	});

	it('pings every 25 seconds while open', () => {
		const live = new LiveSocket('ws://x/ws/live', create);
		live.subscribe('room:1', () => {});
		sockets[0].open();
		vi.advanceTimersByTime(25_000);
		expect(sockets[0].sent).toEqual([
			{ type: 'subscribe', topic: 'room:1' },
			{ type: 'ping' }
		]);
		sockets[0].drop();
		vi.advanceTimersByTime(25_000);
		expect(sockets[0].sent).toHaveLength(2);
	});

	it('close does not report a session end', () => {
		const onEnd = vi.fn();
		const live = new LiveSocket('ws://x/ws/live', create, onEnd);
		live.subscribe('room:1', () => {});
		sockets[0].open();
		const socket = sockets[0];
		live.close();
		socket.drop(SESSION_ENDED);
		expect(onEnd).not.toHaveBeenCalled();
	});

	it('ignores malformed messages', () => {
		const live = new LiveSocket('ws://x/ws/live', create);
		const handler = vi.fn();
		live.subscribe('room:1', handler);
		sockets[0].open();
		sockets[0].onmessage?.({ data: '{nope' } as MessageEvent);
		expect(handler).not.toHaveBeenCalled();
	});
});
