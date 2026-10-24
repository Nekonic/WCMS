<script lang="ts">
	import { api } from '$lib/api/client';
	import { errorMessage, fieldErrors } from '$lib/api/errors';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	let password = $state('');
	let confirm = $state('');
	let code = $state('');
	let error = $state('');
	let fields = $state<Record<string, string>>({});
	let done = $state(false);
	let busy = $state(false);

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		error = '';
		fields = {};
		if (data.info?.needs_password && password !== confirm) {
			fields = { password: '두 비밀번호가 다릅니다.' };
			return;
		}
		busy = true;
		const body = data.info?.needs_password ? { password, code } : { code };
		const { error: failure } = await api.POST('/api/auth/enroll/{token}', {
			params: { path: { token: data.token } },
			body
		});
		busy = false;
		if (failure) {
			error = errorMessage(failure);
			fields = fieldErrors(failure);
			return;
		}
		done = true;
	}
</script>

<section class="card flex w-full max-w-[460px] flex-col gap-3">
	<h1 class="page-title">계정 등록</h1>
	{#if !data.info}
		<p class="error-box">링크가 만료됐거나 이미 사용됐습니다. 관리자에게 새 링크를 받으세요.</p>
	{:else if done}
		<p class="notice-box">등록이 끝났습니다.</p>
		<a class="btn btn-primary" href="/login">로그인하러 가기</a>
	{:else}
		<p class="meta">
			{data.info.username} 계정입니다. 인증 앱(Google Authenticator 등)으로 QR 코드를 찍고, 앱에 나온 6자리 코드를
			입력하세요.
		</p>
		<!-- 서버가 만든 QR SVG다. 사용자 입력이 텍스트로 들어가지 않는다. -->
		<div class="self-start">{@html data.info.qr_svg}</div>
		<p class="meta">직접 입력: <span class="font-mono">{data.info.secret}</span></p>
		{#if error}<p class="error-box" role="alert">{error}</p>{/if}
		<form class="flex flex-col gap-2.5" onsubmit={submit}>
			{#if data.info.needs_password}
				<label class="label" for="password">비밀번호 (10자 이상)</label>
				<input id="password" class="field" type="password" autocomplete="new-password" required bind:value={password} />
				<label class="label" for="confirm">비밀번호 확인</label>
				<input id="confirm" class="field" type="password" autocomplete="new-password" required bind:value={confirm} />
				{#if fields.password}<p class="text-[13px] text-danger">{fields.password}</p>{/if}
			{/if}
			<label class="label" for="code">6자리 코드</label>
			<input id="code" class="field" inputmode="numeric" maxlength="7" required bind:value={code} />
			<button class="btn btn-primary" type="submit" disabled={busy}>등록</button>
		</form>
	{/if}
</section>
