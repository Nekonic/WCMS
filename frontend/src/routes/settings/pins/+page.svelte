<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { api } from '$lib/api/client';
	import { errorMessage } from '$lib/api/errors';
	import type { Pin } from '$lib/api/types';
	import ConfirmButton from '$lib/components/ConfirmButton.svelte';
	import { formatTime } from '$lib/format';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	let multiUse = $state(true);
	let minutes = $state<10 | 60 | 180>(60);
	let created = $state<Pin | null>(null);
	let error = $state('');

	async function create(event: SubmitEvent) {
		event.preventDefault();
		const { data: pin, error: failure } = await api.POST('/api/pins', { body: { multi_use: multiUse, minutes } });
		if (failure || !pin) {
			error = errorMessage(failure);
			return;
		}
		error = '';
		created = pin;
		await invalidateAll();
	}

	async function revoke(id: number) {
		const { error: failure } = await api.DELETE('/api/pins/{id}', { params: { path: { id } } });
		if (failure) {
			error = errorMessage(failure);
			return;
		}
		error = '';
		if (created?.id === id) created = null;
		await invalidateAll();
	}
</script>

<h1 class="page-title">등록 PIN</h1>
{#if error}<p class="error-box" role="alert">{error}</p>{/if}
{#if created}
	<p class="notice-box" role="status">
		새 PIN <strong class="font-mono text-lg">{created.pin}</strong> · {formatTime(created.expires_at)}까지{created.multi_use
			? ' · 여러 대 사용 가능'
			: ''}
	</p>
{/if}

<section class="card max-w-[420px]">
	<h2 class="mb-3 text-base font-semibold">PIN 만들기</h2>
	<form class="flex flex-col gap-2.5" onsubmit={create}>
		<label class="label" for="minutes">유효 시간</label>
		<select id="minutes" class="field" bind:value={minutes}>
			<option value={10}>10분</option>
			<option value={60}>1시간</option>
			<option value={180}>3시간</option>
		</select>
		<label class="flex min-h-11 items-center gap-2"><input type="checkbox" bind:checked={multiUse} /> 여러 대에 사용</label>
		<button class="btn btn-primary" type="submit">만들기</button>
	</form>
</section>

<section class="card">
	<h2 class="mb-3 text-base font-semibold">사용 가능한 PIN</h2>
	{#if data.pins.length === 0}
		<p class="meta">없습니다.</p>
	{:else}
		<table class="w-full border-collapse">
			<thead>
				<tr class="text-left text-xs text-muted">
					<th class="px-3 py-2.5">PIN</th>
					<th class="px-3 py-2.5">만료</th>
					<th class="px-3 py-2.5">방식</th>
					<th class="px-3 py-2.5">사용</th>
					<th class="px-3 py-2.5"><span class="sr-only">폐기</span></th>
				</tr>
			</thead>
			<tbody>
				{#each data.pins as pin (pin.id)}
					<tr class="border-t border-line-soft">
						<td class="px-3 py-2.5 font-mono">{pin.pin}</td>
						<td class="px-3 py-2.5">{formatTime(pin.expires_at)}</td>
						<td class="px-3 py-2.5">{pin.multi_use ? '여러 대' : '1회'}</td>
						<td class="px-3 py-2.5">{pin.used_count}</td>
						<td class="px-3 py-2.5 text-right">
							<ConfirmButton
								label="폐기"
								message="PIN {pin.pin}을(를) 폐기합니다. 이 PIN으로는 더 이상 등록할 수 없습니다."
								danger
								small
								onconfirm={() => revoke(pin.id)}
							/>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{/if}
</section>
