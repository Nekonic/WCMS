<script lang="ts">
	import type { PublicSeat } from '$lib/api/types';

	let { seat }: { seat: PublicSeat } = $props();
</script>

<article class="flex min-h-[72px] flex-col justify-between rounded-[10px] border border-line bg-surface px-3 py-2.5">
	<span class="text-[13px] font-semibold">{seat.label}</span>
	<span class="inline-flex items-center gap-1.5 text-xs {seat.online ? 'font-semibold text-ok' : 'text-muted'}">
		<span class="size-2 rounded-full {seat.online ? 'bg-ok' : 'bg-[#a3a8b2]'}"></span>
		{seat.online ? '켜짐' : '꺼짐'}
	</span>
</article>
