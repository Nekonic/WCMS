const formatter = new Intl.DateTimeFormat('ko-KR', {
	timeZone: 'Asia/Seoul',
	dateStyle: 'medium',
	timeStyle: 'short'
});

export function formatTime(iso: string): string {
	return formatter.format(new Date(iso));
}
