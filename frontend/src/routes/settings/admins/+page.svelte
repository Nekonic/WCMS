<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { api } from '$lib/api/client';
	import { errorMessage, fieldErrors } from '$lib/api/errors';
	import ConfirmButton from '$lib/components/ConfirmButton.svelte';
	import { formatTime } from '$lib/format';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	let username = $state('');
	let link = $state<{ who: string; url: string; expires: string } | null>(null);
	let copied = $state(false);
	let error = $state('');
	let fields = $state<Record<string, string>>({});

	function showLink(who: string, enrollUrl: string, expiresAt: string) {
		link = { who, url: `${location.origin}${enrollUrl}`, expires: formatTime(expiresAt) };
		copied = false;
	}

	async function create(event: SubmitEvent) {
		event.preventDefault();
		error = '';
		fields = {};
		const { data: result, error: failure } = await api.POST('/api/admins', { body: { username } });
		if (failure || !result) {
			error = errorMessage(failure);
			fields = fieldErrors(failure);
			return;
		}
		showLink(result.admin.username, result.enroll_url, result.expires_at);
		username = '';
		await invalidateAll();
	}

	async function reset(id: number, who: string) {
		const { data: result, error: failure } = await api.POST('/api/admins/{id}/reset', { params: { path: { id } } });
		if (failure || !result) {
			error = errorMessage(failure);
			return;
		}
		showLink(who, result.enroll_url, result.expires_at);
		await invalidateAll();
	}

	async function remove(id: number) {
		const { error: failure } = await api.DELETE('/api/admins/{id}', { params: { path: { id } } });
		error = failure ? errorMessage(failure) : '';
		await invalidateAll();
	}

	async function copy() {
		if (link) {
			await navigator.clipboard.writeText(link.url);
			copied = true;
		}
	}
</script>

<h1 class="page-title">관리자 계정</h1>
{#if error}<p class="error-box" role="alert">{error}</p>{/if}

{#if link}
	<section class="notice-box flex flex-col gap-2" role="status">
		<p>{link.who}에게 아래 등록 링크를 전달하세요. {link.expires}까지 한 번만 쓸 수 있습니다.</p>
		<div class="flex flex-wrap items-center gap-2">
			<code class="min-w-0 flex-1 break-all rounded bg-surface px-2 py-1.5 font-mono text-ink">{link.url}</code>
			<button class="btn btn-sm" type="button" onclick={copy}>{copied ? '복사됨' : '복사'}</button>
		</div>
	</section>
{/if}

<section class="card overflow-x-auto">
	<table class="w-full min-w-[560px] border-collapse">
		<thead>
			<tr class="text-left text-xs text-muted">
				<th class="px-3 py-2.5">아이디</th>
				<th class="px-3 py-2.5">인증 앱</th>
				<th class="px-3 py-2.5"><span class="sr-only">관리</span></th>
			</tr>
		</thead>
		<tbody>
			{#each data.admins as admin (admin.id)}
				<tr class="border-t border-line-soft">
					<td class="px-3 py-2.5 font-semibold">{admin.username}{admin.is_self ? ' (나)' : ''}</td>
					<td class="px-3 py-2.5">{admin.totp_enrolled ? '등록됨' : '등록 대기'}</td>
					<td class="flex justify-end gap-2 px-3 py-2.5">
						<ConfirmButton
							label="인증 앱 재설정"
							message="{admin.username}의 인증 앱 재설정 링크를 만듭니다. 이전에 만든 링크는 무효가 됩니다."
							small
							onconfirm={() => reset(admin.id, admin.username)}
						/>
						<ConfirmButton
							label="삭제"
							message="{admin.username} 계정을 삭제합니다."
							danger
							small
							disabled={admin.is_self}
							onconfirm={() => remove(admin.id)}
						/>
					</td>
				</tr>
			{/each}
		</tbody>
	</table>
</section>

<section class="card max-w-[420px]">
	<h2 class="mb-3 text-base font-semibold">관리자 추가</h2>
	<form class="flex flex-col gap-2.5" onsubmit={create}>
		<label class="label" for="username">아이디</label>
		<input id="username" class="field" required bind:value={username} />
		{#if fields.username}<p class="text-[13px] text-danger">{fields.username}</p>{/if}
		<button class="btn btn-primary" type="submit">추가하고 등록 링크 만들기</button>
	</form>
</section>
