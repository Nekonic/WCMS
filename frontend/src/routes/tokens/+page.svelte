<script lang="ts">
  import { onMount } from 'svelte'
  import { api } from '$lib/api.js'

  let tokens: any[] = []
  let usageType = 'single'
  let expiresIn = 600
  let newPin: string | null = null

  onMount(async () => { tokens = await api.tokens() })

  async function create() {
    const res: any = await api.createToken({ usage_type: usageType, expires_in: expiresIn })
    newPin = res.pin
    tokens = await api.tokens()
  }

  async function del(id: number) {
    await api.deleteToken(id)
    tokens = await api.tokens()
  }

  function tokenStatus(t: any): string {
    if (t.isExpired) return '만료됨'
    if (new Date(t.expiresAt) < new Date()) return '시간초과'
    return '유효'
  }

  function fmt(iso: string) {
    return new Date(iso).toLocaleString('ko-KR')
  }
</script>

<h2>등록 토큰</h2>

{#if newPin}
  <div style="background:#e8f5e9;padding:1rem;border-radius:4px;margin-bottom:1rem">
    발급된 PIN: <strong style="font-size:1.5rem">{newPin}</strong>
    <button on:click={() => newPin = null} style="margin-left:1rem">닫기</button>
  </div>
{/if}

<div style="display:flex;gap:0.5rem;align-items:flex-end;margin-bottom:1rem">
  <label>사용 방식
    <select bind:value={usageType}>
      <option value="single">1회용</option>
      <option value="multi">다회용</option>
    </select>
  </label>
  <label>유효 시간(초) <input type="number" bind:value={expiresIn} min="60" style="width:80px" /></label>
  <button on:click={create}>토큰 생성</button>
</div>

<table border="1" cellpadding="6" style="border-collapse:collapse">
  <tr><th>PIN</th><th>종류</th><th>사용 횟수</th><th>상태</th><th>만료 시각</th><th></th></tr>
  {#each tokens as t}
    <tr>
      <td><code>{t.token}</code></td>
      <td>{t.usageType}</td>
      <td>{t.usedCount ?? 0}</td>
      <td>{tokenStatus(t)}</td>
      <td>{fmt(t.expiresAt)}</td>
      <td><button on:click={() => del(t.id)}>삭제</button></td>
    </tr>
  {/each}
</table>