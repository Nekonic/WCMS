<script lang="ts">
	import '../app.css';
	import type { Snippet } from 'svelte';
	import { goto, invalidateAll } from '$app/navigation';
	import { page } from '$app/state';
	import { api } from '$lib/api/client';
	import { resetLive } from '$lib/live';
	import type { LayoutData } from './$types';

	let { data, children }: { data: LayoutData; children: Snippet } = $props();

	const links = [
		{ href: '/', label: '실습실', admin: false, prefix: '/rooms' },
		{ href: '/settings/rooms', label: '실습실 관리', admin: true, prefix: '/settings/rooms' },
		{ href: '/settings/pcs', label: 'PC', admin: true, prefix: '/settings/pcs' },
		{ href: '/settings/pins', label: '등록 PIN', admin: true, prefix: '/settings/pins' },
		{ href: '/settings/admins', label: '관리자 계정', admin: true, prefix: '/settings/admins' },
		{ href: '/settings/audit', label: '기록', admin: true, prefix: '/settings/audit' }
	];

	const visible = $derived(links.filter((link) => !link.admin || data.me.authenticated));

	function active(prefix: string): boolean {
		return page.url.pathname === '/' ? prefix === '/rooms' : page.url.pathname.startsWith(prefix);
	}

	async function logout() {
		// 서버는 로그아웃할 때 열린 소켓을 4401로 닫는다. 먼저 끊어야 세션 종료 처리(/login 이동)가 돌지 않는다
		resetLive();
		await api.POST('/api/auth/logout');
		await invalidateAll();
		await goto('/');
	}
</script>

<div class="flex min-h-screen flex-wrap">
	<nav aria-label="주 메뉴" class="flex flex-[1_1_220px] flex-col gap-1 bg-side px-3.5 py-5">
		<div class="flex items-baseline gap-2 px-3 pt-1 pb-5">
			<span class="text-lg font-bold tracking-wide text-white">WCMS</span>
			<span class="text-xs text-side-muted">2026.1</span>
		</div>
		{#each visible as link (link.href)}
			<a
				href={link.href}
				aria-current={active(link.prefix) ? 'page' : undefined}
				class="flex min-h-11 items-center rounded-lg px-3 text-side-ink no-underline hover:bg-side-hover hover:text-white {active(
					link.prefix
				)
					? 'bg-side-on font-semibold text-white'
					: ''}"
			>
				{link.label}
			</a>
		{/each}
		<div class="flex-1"></div>
		<div class="flex items-center justify-between gap-2 border-t border-side-on px-3 pt-3 text-[13px] text-side-ink">
			{#if data.me.authenticated && data.me.user}
				<span>{data.me.user.username}</span>
				<button type="button" class="cursor-pointer text-side-muted underline" onclick={logout}>로그아웃</button>
			{:else}
				<a href="/login" class="text-side-muted">관리자 로그인</a>
			{/if}
		</div>
	</nav>
	<main class="flex min-w-0 flex-[999_1_560px] flex-col gap-5 px-8 pt-7 pb-10">
		{@render children()}
	</main>
</div>
