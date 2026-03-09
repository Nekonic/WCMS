<script lang="ts">
  import { goto } from '$app/navigation'
  import { api } from '$lib/api.js'
  import { checkAuth } from '$lib/auth.js'

  let username = ''
  let password = ''
  let error = ''

  async function submit() {
    error = ''
    try {
      await api.login(username, password)
      await checkAuth()
      goto('/')
    } catch {
      error = '아이디 또는 비밀번호가 틀렸습니다.'
    }
  }
</script>

<div style="max-width:320px;margin:4rem auto">
  <h2>WCMS 로그인</h2>
  <form on:submit|preventDefault={submit} style="display:flex;flex-direction:column;gap:0.75rem">
    <input bind:value={username} placeholder="아이디" required />
    <input bind:value={password} type="password" placeholder="비밀번호" required />
    {#if error}<p style="color:red;margin:0">{error}</p>{/if}
    <button type="submit">로그인</button>
  </form>
</div>