<script lang="ts">
	let {
		label,
		message,
		confirmLabel = label,
		danger = false,
		small = false,
		disabled = false,
		onconfirm
	}: {
		label: string;
		message: string;
		confirmLabel?: string;
		danger?: boolean;
		small?: boolean;
		disabled?: boolean;
		onconfirm: () => void | Promise<void>;
	} = $props();

	let dialog: HTMLDialogElement | undefined = $state();
	let busy = $state(false);

	async function confirmAction() {
		busy = true;
		try {
			await onconfirm();
		} finally {
			busy = false;
		}
		// 예외가 나면 여기까지 오지 않는다. 대화상자는 열린 채 확인 버튼을 다시 누를 수 있다
		dialog?.close();
	}
</script>

<button
	type="button"
	class="btn {danger ? 'btn-danger' : ''} {small ? 'btn-sm' : ''}"
	{disabled}
	onclick={() => dialog?.showModal()}
>
	{label}
</button>

<dialog bind:this={dialog} class="m-auto w-[min(420px,calc(100%-32px))] rounded-[14px] p-0 backdrop:bg-black/40">
	<div class="flex flex-col gap-4 p-5">
		<p>{message}</p>
		<div class="flex justify-end gap-2">
			<button type="button" class="btn" onclick={() => dialog?.close()}>취소</button>
			<button
				type="button"
				class="btn {danger ? 'btn-danger' : 'btn-primary'}"
				disabled={busy}
				onclick={confirmAction}
			>
				{confirmLabel}
			</button>
		</div>
	</div>
</dialog>
