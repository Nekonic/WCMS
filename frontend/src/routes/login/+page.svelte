<script lang="ts">
	import { goto, invalidateAll } from '$app/navigation';
	import { page } from '$app/state';
	import { api } from '$lib/api/client';
	import { errorMessage } from '$lib/api/errors';
	import { resetLive } from '$lib/live';
	import { safeNext } from '$lib/nav';

	let step = $state<'password' | 'otp'>('password');
	let username = $state('');
	let password = $state('');
	let code = $state('');
	let error = $state('');
	let busy = $state(false);

	async function submitPassword(event: SubmitEvent) {
		event.preventDefault();
		busy = true;
		error = '';
		const { error: failure } = await api.POST('/api/auth/login', { body: { username, password } });
		busy = false;
		password = '';
		if (failure) {
			error = errorMessage(failure);
			return;
		}
		step = 'otp';
	}

	async function submitCode(event: SubmitEvent) {
		event.preventDefault();
		busy = true;
		error = '';
		const { error: failure } = await api.POST('/api/auth/otp', { body: { code } });
		busy = false;
		code = '';
		if (failure) {
			error = errorMessage(failure);
			if ((failure as { error?: string }).error === 'no_pending_login') {
				step = 'password';
			}
			return;
		}
		resetLive();
		await invalidateAll();
		await goto(safeNext(page.url.searchParams.get('next')));
	}
</script>

<section class="card flex w-full max-w-[420px] flex-col gap-3">
	<h1 class="page-title">관리자 로그인</h1>
	{#if error}<p class="error-box" role="alert">{error}</p>{/if}
	{#if step === 'password'}
		<form class="flex flex-col gap-2.5" onsubmit={submitPassword}>
			<label class="label" for="username">아이디</label>
			<input id="username" class="field" autocomplete="username" required bind:value={username} />
			<label class="label" for="password">비밀번호</label>
			<input
				id="password"
				class="field"
				type="password"
				autocomplete="current-password"
				required
				bind:value={password}
			/>
			<button class="btn btn-primary" type="submit" disabled={busy}>다음</button>
		</form>
	{:else}
		<form class="flex flex-col gap-2.5" onsubmit={submitCode}>
			<label class="label" for="code">인증 앱의 6자리 코드</label>
			<input
				id="code"
				class="field"
				inputmode="numeric"
				autocomplete="one-time-code"
				maxlength="7"
				required
				bind:value={code}
			/>
			<button class="btn btn-primary" type="submit" disabled={busy}>로그인</button>
		</form>
	{/if}
</section>
