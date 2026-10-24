<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { api } from '$lib/api/client';
	import { errorMessage } from '$lib/api/errors';
	import ConfirmButton from '$lib/components/ConfirmButton.svelte';
	import { formatTime } from '$lib/format';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
	let error = $state('');

	async function remove(id: number) {
		const { error: failure } = await api.DELETE('/api/pcs/{id}', { params: { path: { id } } });
		error = failure ? errorMessage(failure) : '';
		await invalidateAll();
	}
</script>

<h1 class="page-title">PC</h1>
{#if error}<p class="error-box" role="alert">{error}</p>{/if}

<section class="card overflow-x-auto">
	{#if data.pcs.length === 0}
		<p class="meta">등록된 PC가 없습니다.</p>
	{:else}
		<table class="w-full min-w-[640px] border-collapse">
			<thead>
				<tr class="text-left text-xs text-muted">
					<th class="px-3 py-2.5">호스트 이름</th>
					<th class="px-3 py-2.5">자리</th>
					<th class="px-3 py-2.5">버전</th>
					<th class="px-3 py-2.5">등록</th>
					<th class="px-3 py-2.5"><span class="sr-only">삭제</span></th>
				</tr>
			</thead>
			<tbody>
				{#each data.pcs as pc (pc.id)}
					<tr class="border-t border-line-soft">
						<td class="px-3 py-2.5 font-semibold">{pc.hostname}</td>
						<td class="px-3 py-2.5">{pc.room !== null ? pc.label : '미배정'}</td>
						<td class="px-3 py-2.5 font-mono">{pc.client_version}</td>
						<td class="px-3 py-2.5 text-muted">{formatTime(pc.registered_at)}</td>
						<td class="px-3 py-2.5 text-right">
							<ConfirmButton
								label="삭제"
								message="{pc.hostname}을(를) 삭제합니다. 이 PC의 클라이언트는 연결이 끊기고 다시 등록해야 합니다."
								danger
								small
								onconfirm={() => remove(pc.id)}
							/>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{/if}
</section>
