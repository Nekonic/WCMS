<script lang="ts">
	import AdminTile from '$lib/components/AdminTile.svelte';
	import PublicTile from '$lib/components/PublicTile.svelte';
	import SeatGrid from '$lib/components/SeatGrid.svelte';
	import { invalidateAll } from '$app/navigation';
	import type { LivePC, PublicSeat } from '$lib/api/types';
	import { live } from '$lib/live';
	import { adminRoomReducer, publicRoomReducer, seatKey } from '$lib/live/merge';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const admin = $derived(data.me.authenticated);
	const topic = $derived(admin ? `room:${data.room.id}` : `room:${data.room.id}:public`);

	let pcs = $state(new Map<number, LivePC>());
	let seats = $state(new Map<string, PublicSeat>());
	let problem = $state('');

	$effect(() => {
		const current = topic;
		const isAdmin = admin;
		pcs = new Map();
		seats = new Map();
		problem = '';
		return live().subscribe(current, (message) => {
			if (message.type === 'room_changed') {
				// 크기, 이름, 통로가 바뀌었거나 지워졌을 수 있다. 좌석은 LiveSocket이 다시 구독해 받는다
				void invalidateAll();
				return;
			}
			if (message.type === 'error') {
				if (message.error === 'forbidden_topic') {
					// 서버 재시작 등으로 로그인이 풀렸다. me를 다시 읽으면 비로그인 토픽으로 바뀐다
					void invalidateAll();
					return;
				}
				problem = '실시간 정보를 불러오지 못했습니다.';
				return;
			}
			if (isAdmin) {
				pcs = adminRoomReducer(pcs, message);
			} else {
				seats = publicRoomReducer(seats, message);
			}
		});
	});

	const pcBySeat = $derived(
		new Map(
			[...pcs.values()]
				.filter((pc) => pc.row !== null && pc.col !== null)
				.map((pc) => [seatKey(pc.row as number, pc.col as number), pc])
		)
	);
	const onlineCount = $derived(
		admin ? [...pcs.values()].filter((pc) => pc.online).length : [...seats.values()].filter((s) => s.online).length
	);
	const total = $derived(admin ? pcs.size : seats.size);
</script>

<header class="flex flex-wrap items-end justify-between gap-4">
	<div>
		<h1 class="page-title">실습실 {data.room.name}</h1>
		<p class="meta">온라인 {onlineCount} / {total}</p>
	</div>
</header>

<nav aria-label="실습실" class="flex flex-wrap gap-1.5 self-start rounded-[10px] bg-[#e9ecf1] p-1">
	{#each data.rooms as room (room.id)}
		<a
			href="/rooms/{room.id}"
			aria-current={room.id === data.room.id ? 'page' : undefined}
			class="inline-flex min-h-10 items-center rounded-lg border px-4 font-medium no-underline {room.id === data.room.id
				? 'border-[#d5d9e0] bg-surface font-semibold text-ink'
				: 'border-transparent text-[#3d424d] hover:bg-[#dde1e8]'}"
		>
			{room.name}
		</a>
	{/each}
</nav>

{#if problem}<p class="error-box" role="alert">{problem}</p>{/if}

<section class="card" aria-label="좌석 배치">
	<div class="mb-4 flex justify-center">
		<span class="rounded-md border border-dashed border-[#c4c9d2] px-10 py-1 text-xs text-muted">교탁</span>
	</div>
	<SeatGrid rows={data.room.rows} cols={data.room.cols} aisleAfter={data.room.aisle_after}>
		{#snippet seat(cell)}
			{@const key = seatKey(cell.row, cell.col)}
			{#if admin && pcBySeat.get(key)}
				<AdminTile pc={pcBySeat.get(key)!} />
			{:else if !admin && seats.get(key)}
				<PublicTile seat={seats.get(key)!} />
			{:else}
				<div class="flex min-h-[72px] items-center justify-center rounded-[10px] border border-dashed border-line text-xs text-muted">
					{cell.number}
				</div>
			{/if}
		{/snippet}
	</SeatGrid>
</section>
