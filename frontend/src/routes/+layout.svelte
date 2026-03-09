<script lang="ts">
  import { goto } from '$app/navigation'
  import { user, logout, checkAuth } from '$lib/auth.js'
  import { onMount } from 'svelte'

  onMount(checkAuth)

  async function handleLogout() {
    await logout()
    goto('/login')
  }
</script>

{#if $user}
<nav style="display:flex;gap:1rem;padding:0.5rem 1rem;background:#1a1a2e;color:white;align-items:center">
  <strong>WCMS</strong>
  <a href="/" style="color:white">메인</a>
  <a href="/rooms" style="color:white">실습실</a>
  <a href="/seats" style="color:white">좌석 배치</a>
  <a href="/tokens" style="color:white">토큰</a>
  <a href="/versions" style="color:white">버전</a>
  <a href="/logs" style="color:white">이벤트</a>
  <span style="margin-left:auto">{$user.username}</span>
  <button on:click={handleLogout}>로그아웃</button>
</nav>
{/if}

<main style="padding:1rem">
  <slot />
</main>