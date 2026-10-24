const BASE = 'http://local.invalid';

export function safeNext(value: string | null): string {
	if (!value || !value.startsWith('/') || value.startsWith('//') || value.startsWith('/\\')) {
		return '/';
	}
	// URL 파서는 탭/개행을 지우므로 '/\t/host'가 외부 주소가 된다. 고정 기준에 풀어 origin이 같은지 확인한다
	try {
		return new URL(value, BASE).origin === BASE ? value : '/';
	} catch {
		return '/';
	}
}
