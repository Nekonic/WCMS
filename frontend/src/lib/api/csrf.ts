export function csrfToken(cookie: string): string | null {
	for (const part of cookie.split(';')) {
		const [name, ...rest] = part.trim().split('=');
		if (name === 'csrftoken') {
			return decodeURIComponent(rest.join('='));
		}
	}
	return null;
}
