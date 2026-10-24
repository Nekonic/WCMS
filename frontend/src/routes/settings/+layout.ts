import { redirect } from '@sveltejs/kit';
import type { Me } from '$lib/api/types';
import type { LayoutLoad } from './$types';

export const load: LayoutLoad = async ({ parent, url }) => {
	// settings 아래에 페이지가 생기기 전에는 생성된 타입이 부모 데이터를 비워 두므로 형태를 직접 지정한다
	const { me } = (await parent()) as { me: Me };
	if (!me.authenticated) {
		redirect(307, `/login?next=${encodeURIComponent(url.pathname + url.search)}`);
	}
};
