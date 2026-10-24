<script lang="ts">
	import type { Snippet } from 'svelte';
	import { gridCells, gridColumns, type Cell } from '$lib/grid';

	type SeatCell = Extract<Cell, { kind: 'seat' }>;

	let {
		rows,
		cols,
		aisleAfter,
		seat
	}: { rows: number; cols: number; aisleAfter: number | null; seat: Snippet<[SeatCell]> } = $props();

	const cells = $derived(gridCells(rows, cols, aisleAfter));
	const columns = $derived(gridColumns(cols, aisleAfter));
</script>

<div class="overflow-x-auto">
	<div class="grid min-w-[960px] gap-3" style:grid-template-columns={columns}>
		{#each cells as cell (cell.kind === 'seat' ? `${cell.row}:${cell.col}` : cell.key)}
			{#if cell.kind === 'aisle'}
				<div aria-hidden="true"></div>
			{:else}
				{@render seat(cell)}
			{/if}
		{/each}
	</div>
</div>
