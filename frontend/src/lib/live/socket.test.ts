import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { LiveSocket, SESSION_ENDED, type LiveStatus } from './socket';

class FakeSocket {
	readyState = 0;
	sent: unknown[] = [];
	onopen: ((ev: Event) => unknown) | null = null;
	onmessage: ((ev: MessageEvent) => unknown) | null = null;
	onclose: ((ev: CloseEvent) => unknown) | null = null;
	send(data: string) {
		this.sent.push(JSON.parse(data));
	}
	closed = false;
	close() {
		this.closed = true;
	}
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
	// 재접속 대기 = delay + random*1000. 0.5로 고정해 1.5초, 2.5초, 4.5초 …가 되게 한다
	vi.spyOn(Math, 'random').mockReturnValue(0.5);
});
afterEach(() => {
	vi.useRealTimers();
	vi.restoreAllMocks();
});

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

	it('reports connection status', () => {
		const live = new LiveSocket('ws://x/ws/live', create);
		const seen: LiveStatus[] = [];
		const off = live.onStatus((status) => seen.push(status));
		expect(seen).toEqual(['closed']);
		live.subscribe('room:1', () => {});
		expect(seen).toEqual(['closed', 'connecting']);
		sockets[0].open();
		expect(live.status).toBe('open');
		sockets[0].drop();
		expect(seen).toEqual(['closed', 'connecting', 'open', 'closed']);
		vi.advanceTimersByTime(1500);
		expect(seen).toEqual(['closed', 'connecting', 'open', 'closed', 'connecting']);
		off();
		sockets[1].open();
		expect(seen).toHaveLength(5);
		expect(live.status).toBe('open');
	});

	it('reports closed after close()', () => {
		const live = new LiveSocket('ws://x/ws/live', create);
		live.subscribe('room:1', () => {});
		sockets[0].open();
		live.close();
		expect(live.status).toBe('closed');
	});

	it('closes and reconnects when no pong arrives within 10 seconds of a ping', () => {
		const live = new LiveSocket('ws://x/ws/live', create);
		const seen: LiveStatus[] = [];
		live.onStatus((status) => seen.push(status));
		live.subscribe('room:1', () => {});
		sockets[0].open();
		vi.advanceTimersByTime(25_000);
		expect(sockets[0].sent).toContainEqual({ type: 'ping' });
		vi.advanceTimersByTime(9_999);
		expect(sockets[0].closed).toBe(false);
		vi.advanceTimersByTime(1);
		expect(sockets[0].closed).toBe(true);
		expect(live.status).toBe('closed');
		vi.advanceTimersByTime(1500);
		expect(sockets).toHaveLength(2);
		sockets[1].open();
		expect(sockets[1].sent).toEqual([{ type: 'subscribe', topic: 'room:1' }]);
		expect(seen.at(-1)).toBe('open');
	});

	it('a pong cancels the watchdog', () => {
		const live = new LiveSocket('ws://x/ws/live', create);
		live.subscribe('room:1', () => {});
		sockets[0].open();
		vi.advanceTimersByTime(25_000);
		sockets[0].receive({ type: 'pong' });
		vi.advanceTimersByTime(10_000);
		expect(sockets[0].closed).toBe(false);
		expect(sockets).toHaveLength(1);
	});

	it('any message cancels the watchdog', () => {
		const live = new LiveSocket('ws://x/ws/live', create);
		live.subscribe('room:1', () => {});
		sockets[0].open();
		vi.advanceTimersByTime(25_000);
		sockets[0].receive({ type: 'pc', topic: 'room:1', pc: { id: 1 } });
		vi.advanceTimersByTime(10_000);
		expect(sockets[0].closed).toBe(false);
		expect(live.status).toBe('open');
	});

	it('a late close event from a watchdog-closed socket is ignored', () => {
		const live = new LiveSocket('ws://x/ws/live', create);
		live.subscribe('room:1', () => {});
		sockets[0].open();
		vi.advanceTimersByTime(35_000);
		const old = sockets[0];
		vi.advanceTimersByTime(1500);
		expect(sockets).toHaveLength(2);
		sockets[1].open();
		old.drop();
		vi.advanceTimersByTime(60_000);
		// 이전 소켓의 늦은 onclose가 새 연결을 끊거나 재접속을 더 만들지 않는다
		expect(live.status).not.toBe('closed');
		expect(sockets.filter((socket) => !socket.closed).length).toBeGreaterThan(0);
	});

	it('re-subscribes on room_changed only for subscribed topics', () => {
		const live = new LiveSocket('ws://x/ws/live', create);
		live.subscribe('room:1', () => {});
		sockets[0].open();
		sockets[0].receive({ type: 'room_changed', topic: 'room:2' });
		expect(sockets[0].sent).toEqual([{ type: 'subscribe', topic: 'room:1' }]);
	});

	it('ensureOpen clears a pending reconnect timer', () => {
		const live = new LiveSocket('ws://x/ws/live', create);
		live.subscribe('room:1', () => {});
		sockets[0].open();
		sockets[0].drop();
		// 재접속 대기(1.5초) 중에 새 구독이 들어오면 바로 연다
		live.subscribe('room:2', () => {});
		expect(sockets).toHaveLength(2);
		// 그 연결도 곧 끊기면 다음 대기는 2.5초다. 처음 예약한 1.5초 타이머가 남아 있으면 안 된다
		sockets[1].drop();
		vi.advanceTimersByTime(1500);
		expect(sockets).toHaveLength(2);
		vi.advanceTimersByTime(1000);
		expect(sockets).toHaveLength(3);
	});

	it('keeps growing the backoff when sockets close before becoming stable', () => {
		const live = new LiveSocket('ws://x/ws/live', create);
		live.subscribe('room:1', () => {});
		sockets[0].open();
		sockets[0].drop();
		vi.advanceTimersByTime(1500);
		expect(sockets).toHaveLength(2);
		sockets[1].open();
		sockets[1].drop();
		vi.advanceTimersByTime(2499);
		expect(sockets).toHaveLength(2);
		vi.advanceTimersByTime(1);
		expect(sockets).toHaveLength(3);
	});

	it('resets the backoff after the first message', () => {
		const live = new LiveSocket('ws://x/ws/live', create);
		live.subscribe('room:1', () => {});
		sockets[0].open();
		sockets[0].drop();
		vi.advanceTimersByTime(1500);
		sockets[1].open();
		sockets[1].drop();
		vi.advanceTimersByTime(2500);
		expect(sockets).toHaveLength(3);
		sockets[2].open();
		sockets[2].receive({ type: 'snapshot', topic: 'room:1', pcs: [] });
		sockets[2].drop();
		vi.advanceTimersByTime(1500);
		expect(sockets).toHaveLength(4);
	});

	it('resets the backoff after staying open for 5 seconds', () => {
		const live = new LiveSocket('ws://x/ws/live', create);
		live.subscribe('room:1', () => {});
		sockets[0].open();
		sockets[0].drop();
		vi.advanceTimersByTime(1500);
		sockets[1].open();
		sockets[1].drop();
		vi.advanceTimersByTime(2500);
		sockets[2].open();
		vi.advanceTimersByTime(5_000);
		sockets[2].drop();
		vi.advanceTimersByTime(1500);
		expect(sockets).toHaveLength(4);
	});

	it('a throwing handler does not stop the others', () => {
		const error = vi.spyOn(console, 'error').mockImplementation(() => {});
		const live = new LiveSocket('ws://x/ws/live', create);
		const after = vi.fn();
		live.subscribe('room:1', () => {
			throw new Error('boom');
		});
		live.subscribe('room:1', after);
		sockets[0].open();
		sockets[0].receive({ type: 'pc', topic: 'room:1', pc: { id: 1 } });
		expect(after).toHaveBeenCalledOnce();
		expect(error).toHaveBeenCalledOnce();
	});

	it('a throwing status listener does not stop the socket', () => {
		vi.spyOn(console, 'error').mockImplementation(() => {});
		const live = new LiveSocket('ws://x/ws/live', create);
		const later = vi.fn();
		live.onStatus((status) => {
			if (status === 'open') throw new Error('boom');
		});
		live.onStatus(later);
		live.subscribe('room:1', () => {});
		sockets[0].open();
		expect(later).toHaveBeenLastCalledWith('open');
		expect(sockets[0].sent).toEqual([{ type: 'subscribe', topic: 'room:1' }]);
	});
});
