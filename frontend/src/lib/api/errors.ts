const FALLBACK = '요청을 처리하지 못했습니다.';

function isRecord(value: unknown): value is Record<string, unknown> {
	return typeof value === 'object' && value !== null;
}

export function errorMessage(error: unknown): string {
	if (isRecord(error) && typeof error.detail === 'string' && error.detail) {
		return error.detail;
	}
	return FALLBACK;
}

export function fieldErrors(error: unknown): Record<string, string> {
	if (!isRecord(error) || !isRecord(error.fields)) {
		return {};
	}
	const result: Record<string, string> = {};
	for (const [field, value] of Object.entries(error.fields)) {
		const texts = (Array.isArray(value) ? value : [value]).filter((item): item is string => typeof item === 'string');
		// 좌석 목록처럼 항목별 오류가 중첩되면 문자열이 없다. 그때는 일반 문구를 쓴다
		result[field] = texts.length ? texts.join(' ') : '입력값을 확인하세요.';
	}
	return result;
}
