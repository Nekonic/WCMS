<script lang="ts">
	import { goto, invalidateAll } from '$app/navigation';
	import { api } from '$lib/api/client';
	import { errorMessage, fieldErrors } from '$lib/api/errors';
	import ConfirmButton from '$lib/components/ConfirmButton.svelte';
	import SeatGrid from '$lib/components/SeatGrid.svelte';
	import { seatsOutside } from '$lib/grid';
	import { seatKey } from '$lib/live/merge';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	let name = $state('');
	let rows = $state(1);
	let cols = $state(1);
	let aisle = $state<number | null>(null);
	let assignment = $state<Record<string, number | ''>>({});
	let error = $state('');
	let fields = $state<Record<string, string>>({});
	let saved = $state('');
	let shrinkDialog: HTMLDialogElement | undefined = $state();
	let unseated = $state(0);
	let sizeBusy = $state(false);

	$effect.pre(() => {
		name = data.room.name;
		rows = data.room.rows;
		cols = data.room.cols;
		aisle = data.room.aisle_after ?? null;
		// 모든 칸을 '' (비움)으로 채운 뒤 서버에 있는 배치를 덮어쓴다. 빈 칸이 undefined면 새로고침 뒤 select가 빈 채로 보인다
		const next: Record<string, number | ''> = {};
		for (let row = 0; row < data.room.rows; row++) {
			for (let col = 0; col < data.room.cols; col++) {
				next[seatKey(row, col)] = '';
			}
		}
		for (const s of data.seats) {
			next[seatKey(s.row, s.col)] = s.pc;
		}
		assignment = next;
	});

	function pcText(pc: PageData['pcs'][number]): string {
		return pc.room !== null && pc.room !== data.room.id ? `${pc.hostname} (${pc.label})` : pc.hostname;
	}

	async function saveSize(event: SubmitEvent) {
		event.preventDefault();
		// 서버는 새 크기 밖에 앉은 PC의 자리 배정을 모두 푼다. 그런 PC가 있으면 먼저 확인받는다
		unseated = seatsOutside(data.seats, rows, cols);
		if (unseated > 0) {
			shrinkDialog?.showModal();
			return;
		}
		await patchSize();
	}

	async function confirmShrink() {
		sizeBusy = true;
		try {
			await patchSize();
		} finally {
			sizeBusy = false;
			shrinkDialog?.close();
		}
	}

	async function patchSize() {
		error = '';
		fields = {};
		saved = '';
		const { error: failure } = await api.PATCH('/api/rooms/{id}', {
			params: { path: { id: data.room.id } },
			body: { name, rows, cols, aisle_after: aisle || null }
		});
		if (failure) {
			error = errorMessage(failure);
			fields = fieldErrors(failure);
			return;
		}
		saved = '저장했습니다.';
		await invalidateAll();
	}

	async function saveSeats() {
		error = '';
		saved = '';
		// 비운 자리는 ''이므로 보내지 않는다
		const seats = Object.entries(assignment)
			.filter(([, pc]) => pc !== '')
			.map(([key, pc]) => {
				const [row, col] = key.split(':').map(Number);
				return { row, col, pc: pc as number };
			});
		const { error: failure } = await api.PUT('/api/rooms/{id}/seats', {
			params: { path: { id: data.room.id } },
			body: { seats }
		});
		if (failure) {
			error = [errorMessage(failure), ...Object.values(fieldErrors(failure))].join(' ');
			return;
		}
		saved = '좌석 배치를 저장했습니다.';
		await invalidateAll();
	}

	async function remove() {
		const { error: failure } = await api.DELETE('/api/rooms/{id}', { params: { path: { id: data.room.id } } });
		if (failure) {
			error = errorMessage(failure);
			return;
		}
		await goto('/settings/rooms');
	}
</script>

<header class="flex flex-wrap items-end justify-between gap-4">
	<div>
		<h1 class="page-title">{data.room.name} 자리 배치</h1>
		<p class="meta"><a href="/settings/rooms">실습실 관리</a></p>
	</div>
	<ConfirmButton
		label="실습실 삭제"
		message="{data.room.name} 실습실을 삭제합니다. 앉아 있던 PC는 모두 자리 미배정이 됩니다."
		danger
		onconfirm={remove}
	/>
</header>

{#if error}<p class="error-box" role="alert">{error}</p>{/if}
{#if saved}<p class="notice-box" role="status">{saved}</p>{/if}

<section class="card">
	<h2 class="mb-3 text-base font-semibold">크기</h2>
	<form class="flex flex-wrap items-end gap-4" onsubmit={saveSize}>
		<div class="flex flex-col gap-1.5">
			<label class="label" for="name">이름</label>
			<input id="name" class="field" required bind:value={name} />
		</div>
		<div class="flex w-24 flex-col gap-1.5">
			<label class="label" for="rows">줄 수</label>
			<input id="rows" class="field" type="number" min="1" max="20" bind:value={rows} />
		</div>
		<div class="flex w-24 flex-col gap-1.5">
			<label class="label" for="cols">열 수</label>
			<input id="cols" class="field" type="number" min="1" max="20" bind:value={cols} />
		</div>
		<div class="flex w-40 flex-col gap-1.5">
			<label class="label" for="aisle">통로 (N열 뒤)</label>
			<input id="aisle" class="field" type="number" min="1" bind:value={aisle} />
		</div>
		<button class="btn" type="submit">크기 저장</button>
	</form>
	{#each Object.entries(fields) as [field, message] (field)}
		<p class="mt-2 text-[13px] text-danger">{message}</p>
	{/each}
</section>

<dialog bind:this={shrinkDialog} class="m-auto w-[min(420px,calc(100%-32px))] rounded-[14px] p-0 backdrop:bg-black/40">
	<div class="flex flex-col gap-4 p-5">
		<p>줄이면 {unseated}대의 자리 배정이 풀립니다.</p>
		<div class="flex justify-end gap-2">
			<button type="button" class="btn" onclick={() => shrinkDialog?.close()}>취소</button>
			<button type="button" class="btn btn-danger" disabled={sizeBusy} onclick={confirmShrink}>줄이기</button>
		</div>
	</div>
</dialog>

<section class="card">
	<div class="mb-3 flex items-center justify-between">
		<h2 class="text-base font-semibold">자리</h2>
		<button class="btn btn-primary" type="button" onclick={saveSeats}>좌석 배치 저장</button>
	</div>
	<SeatGrid rows={data.room.rows} cols={data.room.cols} aisleAfter={data.room.aisle_after ?? null}>
		{#snippet seat(cell)}
			{@const key = seatKey(cell.row, cell.col)}
			<div class="flex min-w-0 flex-col gap-1">
				<label class="text-xs text-muted" for="seat-{key}">{cell.number}</label>
				<select id="seat-{key}" class="field w-full" bind:value={assignment[key]}>
					<option value="">비움</option>
					{#each data.pcs as pc (pc.id)}
						<option value={pc.id}>{pcText(pc)}</option>
					{/each}
				</select>
			</div>
		{/snippet}
	</SeatGrid>
</section>
