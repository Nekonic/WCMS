<script lang="ts">
	import { onMount } from 'svelte';
	import { api } from '$lib/api/client';
	import type { AuditLog } from '$lib/api/types';
	import { formatTime } from '$lib/format';

	let entries = $state<AuditLog[]>([]);
	let cursor = $state<string | null>(null);
	let loading = $state(false);

	function cursorOf(next: string | null | undefined): string | null {
		return next ? new URL(next, location.origin).searchParams.get('cursor') : null;
	}

	async function load(from: string | null) {
		loading = true;
		const { data } = await api.GET('/api/audit', { params: { query: from ? { cursor: from } : {} } });
		loading = false;
		if (data) {
			entries = [...entries, ...data.results];
			cursor = cursorOf(data.next);
		}
	}

	onMount(() => {
		void load(null);
	});
</script>

<h1 class="page-title">기록</h1>

<section class="card overflow-x-auto">
	<table class="w-full min-w-[640px] border-collapse">
		<thead>
			<tr class="text-left text-xs text-muted">
				<th class="px-3 py-2.5">시각</th>
				<th class="px-3 py-2.5">관리자</th>
				<th class="px-3 py-2.5">동작</th>
				<th class="px-3 py-2.5">대상</th>
			</tr>
		</thead>
		<tbody>
			{#each entries as entry (entry.id)}
				<tr class="border-t border-line-soft">
					<td class="px-3 py-2.5 text-muted">{formatTime(entry.created_at)}</td>
					<td class="px-3 py-2.5">{entry.actor ?? '-'}</td>
					<td class="px-3 py-2.5 font-mono">{entry.action}</td>
					<td class="px-3 py-2.5 font-mono">{entry.target}</td>
				</tr>
			{/each}
		</tbody>
	</table>
	{#if cursor}
		<div class="mt-3 flex justify-center">
			<button class="btn btn-sm" type="button" disabled={loading} onclick={() => load(cursor)}>더 보기</button>
		</div>
	{/if}
</section>
