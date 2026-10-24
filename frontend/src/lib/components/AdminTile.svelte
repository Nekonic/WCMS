<script lang="ts">
	import type { LivePC } from '$lib/api/types';
	import { pcState } from '$lib/pcState';

	let { pc }: { pc: LivePC } = $props();

	const display = $derived(pcState(pc));
	const screen: Record<string, string> = {
		offline: 'bg-[#2a2d34] text-[#a9afbb]',
		no_user: 'bg-[#3b4a5a] text-white',
		locked: 'bg-[#4a3f2a] text-white',
		active: 'bg-[#2f5c7a] text-white'
	};
	const foreground = $derived(
		pc.foreground ? [pc.foreground.process, pc.foreground.title].filter(Boolean).join(' · ') : ''
	);
</script>

<article class="flex min-h-[120px] flex-col overflow-hidden rounded-[10px] border border-line bg-surface" data-pc-id={pc.id}>
	<div class="flex aspect-[16/10] items-center justify-center text-xs {screen[display.key]}">{display.label}</div>
	<div class="flex items-center justify-between gap-1.5 px-2.5 py-2">
		<span class="text-[13px] font-semibold">{pc.label}</span>
		<span class="text-xs {display.key === 'active' ? 'font-semibold text-ok' : 'text-muted'}">{display.label}</span>
	</div>
	<div class="flex flex-col gap-0.5 px-2.5 pb-2 text-xs text-muted">
		<span class="truncate">{pc.user}</span>
		<span class="truncate">{foreground}</span>
	</div>
</article>
