import type { Handler, ServerMessage } from './types';

export const SESSION_ENDED = 4401;
const OPEN = 1;
const MIN_DELAY = 1000;
const MAX_DELAY = 30_000;
const PING_INTERVAL = 25_000;
// ping을 보낸 뒤 이 시간 안에 아무 메시지도 오지 않으면 연결이 죽은 것으로 본다
const PONG_TIMEOUT = 10_000;
// 이만큼 열려 있었거나 메시지를 하나라도 받았으면 안정된 연결로 보고 재접속 대기를 처음으로 돌린다
const STABLE_AFTER = 5_000;
const DROPPED = 1006;

export type LiveStatus = 'connecting' | 'open' | 'closed';
export type StatusListener = (status: LiveStatus) => void;

export interface SocketLike {
	readyState: number;
	send(data: string): void;
	close(): void;
	onopen: ((ev: Event) => unknown) | null;
	onmessage: ((ev: MessageEvent) => unknown) | null;
	onclose: ((ev: CloseEvent) => unknown) | null;
}

export class LiveSocket {
	private socket: SocketLike | null = null;
	private readonly topics = new Map<string, Set<Handler>>();
	private readonly listeners = new Set<StatusListener>();
	private current: LiveStatus = 'closed';
	private delay = MIN_DELAY;
	private timer: ReturnType<typeof setTimeout> | null = null;
	private pinger: ReturnType<typeof setInterval> | null = null;
	private watchdog: ReturnType<typeof setTimeout> | null = null;
	private stableTimer: ReturnType<typeof setTimeout> | null = null;
	private stopped = false;

	constructor(
		private readonly url: string,
		private readonly create: (url: string) => SocketLike = (url) => new WebSocket(url),
		private readonly onSessionEnd: () => void = () => {}
	) {}

	get status(): LiveStatus {
		return this.current;
	}

	/** 연결 상태를 알린다. 등록하자마자 현재 상태로 한 번 부른다 */
	onStatus(listener: StatusListener): () => void {
		this.listeners.add(listener);
		this.notify(listener, this.current);
		return () => {
			this.listeners.delete(listener);
		};
	}

	subscribe(topic: string, handler: Handler): () => void {
		let handlers = this.topics.get(topic);
		if (!handlers) {
			handlers = new Set();
			this.topics.set(topic, handlers);
			this.send({ type: 'subscribe', topic });
		}
		handlers.add(handler);
		this.ensureOpen();
		return () => {
			const current = this.topics.get(topic);
			if (!current) return;
			current.delete(handler);
			if (current.size === 0) {
				this.topics.delete(topic);
				this.send({ type: 'unsubscribe', topic });
			}
		};
	}

	close(): void {
		this.stopped = true;
		this.clearReconnect();
		this.clearTimers();
		if (this.socket) {
			this.detach(this.socket);
			this.socket.close();
		}
		this.socket = null;
		this.setStatus('closed');
	}

	private send(message: object): void {
		if (this.socket?.readyState === OPEN) {
			this.socket.send(JSON.stringify(message));
		}
	}

	private ensureOpen(): void {
		if (this.socket || this.stopped) return;
		this.clearReconnect();
		const socket = this.create(this.url);
		this.socket = socket;
		this.setStatus('connecting');
		socket.onopen = () => {
			for (const topic of this.topics.keys()) {
				socket.send(JSON.stringify({ type: 'subscribe', topic }));
			}
			this.clearTimers();
			this.pinger = setInterval(() => this.ping(), PING_INTERVAL);
			this.stableTimer = setTimeout(() => this.markStable(), STABLE_AFTER);
			this.setStatus('open');
		};
		socket.onmessage = (event) => {
			this.markStable();
			if (this.watchdog) clearTimeout(this.watchdog);
			this.watchdog = null;
			this.dispatch(event.data);
		};
		socket.onclose = (event) => this.handleClose(socket, event.code);
	}

	private ping(): void {
		if (this.socket?.readyState !== OPEN) return;
		this.send({ type: 'ping' });
		if (this.watchdog) clearTimeout(this.watchdog);
		this.watchdog = setTimeout(() => {
			this.watchdog = null;
			const socket = this.socket;
			if (!socket) return;
			// 죽은 연결은 브라우저가 onclose를 늦게 부를 수 있다. 핸들러를 떼고 끊긴 것으로 바로 처리한다
			this.detach(socket);
			socket.close();
			this.handleClose(socket, DROPPED);
		}, PONG_TIMEOUT);
	}

	private handleClose(socket: SocketLike, code: number): void {
		if (socket !== this.socket) return;
		this.socket = null;
		this.clearTimers();
		this.setStatus('closed');
		if (code === SESSION_ENDED) {
			this.stopped = true;
			this.onSessionEnd();
			return;
		}
		if (this.stopped || this.topics.size === 0) return;
		const wait = this.delay + Math.random() * 1000;
		this.delay = Math.min(this.delay * 2, MAX_DELAY);
		this.timer = setTimeout(() => {
			this.timer = null;
			this.ensureOpen();
		}, wait);
	}

	private markStable(): void {
		this.delay = MIN_DELAY;
		if (this.stableTimer) clearTimeout(this.stableTimer);
		this.stableTimer = null;
	}

	private detach(socket: SocketLike): void {
		socket.onopen = null;
		socket.onmessage = null;
		socket.onclose = null;
	}

	private clearReconnect(): void {
		if (this.timer) clearTimeout(this.timer);
		this.timer = null;
	}

	private clearTimers(): void {
		if (this.pinger) clearInterval(this.pinger);
		if (this.watchdog) clearTimeout(this.watchdog);
		if (this.stableTimer) clearTimeout(this.stableTimer);
		this.pinger = null;
		this.watchdog = null;
		this.stableTimer = null;
	}

	private setStatus(status: LiveStatus): void {
		if (status === this.current) return;
		this.current = status;
		for (const listener of [...this.listeners]) {
			this.notify(listener, status);
		}
	}

	private notify(listener: StatusListener, status: LiveStatus): void {
		try {
			listener(status);
		} catch (error) {
			console.error(error);
		}
	}

	private dispatch(raw: unknown): void {
		if (typeof raw !== 'string') return;
		let message: ServerMessage;
		try {
			message = JSON.parse(raw);
		} catch {
			return;
		}
		if (typeof message !== 'object' || message === null) return;
		const topic = 'topic' in message ? message.topic : undefined;
		if (typeof topic !== 'string') return;
		if (message.type === 'room_changed' && this.topics.has(topic)) {
			this.send({ type: 'subscribe', topic });
		}
		for (const handler of [...(this.topics.get(topic) ?? [])]) {
			try {
				handler(message);
			} catch (error) {
				console.error(error);
			}
		}
	}
}
