import type { Handler, ServerMessage } from './types';

export const SESSION_ENDED = 4401;
const OPEN = 1;
const MAX_DELAY = 30_000;
const PING_INTERVAL = 25_000;

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
	private delay = 1000;
	private timer: ReturnType<typeof setTimeout> | null = null;
	private pinger: ReturnType<typeof setInterval> | null = null;
	private stopped = false;

	constructor(
		private readonly url: string,
		private readonly create: (url: string) => SocketLike = (url) => new WebSocket(url),
		private readonly onSessionEnd: () => void = () => {}
	) {}

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
		if (this.timer) clearTimeout(this.timer);
		this.stopPing();
		if (this.socket) {
			this.socket.onclose = null;
			this.socket.onmessage = null;
			this.socket.close();
		}
		this.socket = null;
	}

	private send(message: object): void {
		if (this.socket?.readyState === OPEN) {
			this.socket.send(JSON.stringify(message));
		}
	}

	private ensureOpen(): void {
		if (this.socket || this.stopped) return;
		const socket = this.create(this.url);
		this.socket = socket;
		socket.onopen = () => {
			this.delay = 1000;
			for (const topic of this.topics.keys()) {
				socket.send(JSON.stringify({ type: 'subscribe', topic }));
			}
			this.stopPing();
			this.pinger = setInterval(() => this.send({ type: 'ping' }), PING_INTERVAL);
		};
		socket.onmessage = (event) => this.dispatch(event.data);
		socket.onclose = (event) => {
			this.socket = null;
			this.stopPing();
			if (event.code === SESSION_ENDED) {
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
		};
	}

	private stopPing(): void {
		if (this.pinger) clearInterval(this.pinger);
		this.pinger = null;
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
		if (message.type === 'room_changed') {
			this.send({ type: 'subscribe', topic });
		}
		for (const handler of this.topics.get(topic) ?? []) {
			handler(message);
		}
	}
}
