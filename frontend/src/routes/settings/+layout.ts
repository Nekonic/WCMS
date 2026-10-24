import { redirect } from '@sveltejs/kit';
import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ parent, url }) => {
	const { me } = await parent();
	if (!me.authenticated) {
		redirect(307, `/login?next=${encodeURIComponent(url.pathname + url.search)}`);
	}
};
