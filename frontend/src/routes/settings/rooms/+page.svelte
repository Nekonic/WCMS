<script lang="ts">
	import { goto } from '$app/navigation';
	import { api } from '$lib/api/client';
	import { errorMessage, fieldErrors } from '$lib/api/errors';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	let name = $state('');
	let rows = $state(5);
	let cols = $state(8);
	let aisle = $state<number | null>(4);
	let sortOrder = $state(0);
	let error = $state('');
	let fields = $state<Record<string, string>>({});

	async function create(event: SubmitEvent) {
		event.preventDefault();
		error = '';
		fields = {};
		const { data: room, error: failure } = await api.POST('/api/rooms', {
			body: { name, rows, cols, aisle_after: aisle || null, sort_order: sortOrder }
		});
		if (failure || !room) {
			error = errorMessage(failure);
			fields = fieldErrors(failure);
			return;
		}
		await goto(`/settings/rooms/${room.id}`);
	}
</script>

<h1 class="page-title">실습실 관리</h1>

<section class="card">
	<h2 class="mb-3 text-base font-semibold">실습실</h2>
	{#if data.rooms.length === 0}
		<p class="meta">아직 없습니다.</p>
	{:else}
		<table class="w-full border-collapse">
			<thead>
				<tr class="text-left text-xs text-muted">
					<th class="px-3 py-2.5">이름</th>
					<th class="px-3 py-2.5">크기</th>
					<th class="px-3 py-2.5"><span class="sr-only">편집</span></th>
				</tr>
			</thead>
			<tbody>
				{#each data.rooms as room (room.id)}
					<tr class="border-t border-line-soft">
						<td class="px-3 py-2.5">{room.name}</td>
						<td class="px-3 py-2.5">{room.rows} × {room.cols}</td>
						<td class="px-3 py-2.5 text-right"><a href="/settings/rooms/{room.id}">자리 배치</a></td>
					</tr>
				{/each}
			</tbody>
		</table>
	{/if}
</section>

<section class="card max-w-[480px]">
	<h2 class="mb-3 text-base font-semibold">실습실 추가</h2>
	{#if error}<p class="error-box mb-3" role="alert">{error}</p>{/if}
	<form class="flex flex-col gap-2.5" onsubmit={create}>
		<label class="label" for="name">이름</label>
		<input id="name" class="field" required bind:value={name} />
		{#if fields.name}<p class="text-[13px] text-danger">{fields.name}</p>{/if}
		<div class="flex gap-3">
			<div class="flex flex-1 flex-col gap-1.5">
				<label class="label" for="rows">줄 수</label>
				<input id="rows" class="field" type="number" min="1" max="20" required bind:value={rows} />
			</div>
			<div class="flex flex-1 flex-col gap-1.5">
				<label class="label" for="cols">열 수</label>
				<input id="cols" class="field" type="number" min="1" max="20" required bind:value={cols} />
			</div>
		</div>
		<label class="label" for="aisle">통로 위치 (N번째 열 뒤, 비우면 없음)</label>
		<input id="aisle" class="field" type="number" min="1" bind:value={aisle} />
		{#if fields.aisle_after}<p class="text-[13px] text-danger">{fields.aisle_after}</p>{/if}
		<label class="label" for="sort">정렬 순서</label>
		<input id="sort" class="field" type="number" min="0" bind:value={sortOrder} />
		<button class="btn btn-primary" type="submit">추가</button>
	</form>
</section>
