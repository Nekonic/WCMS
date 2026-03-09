<script lang="ts">
  import { onMount } from 'svelte'
  import { api } from '$lib/api.js'

  let rooms: any[] = []
  let name = '', rows = 6, cols = 8, desc = ''
  let message = ''

  onMount(async () => { rooms = await api.rooms() })

  async function create() {
    await api.createRoom({ room_name: name, rows, cols, description: desc })
    rooms = await api.rooms()
    name = ''; desc = ''
    message = '실습실이 생성되었습니다.'
  }

  async function del(id: number) {
    if (!confirm('삭제하시겠습니까?')) return
    await api.deleteRoom(id)
    rooms = await api.rooms()
  }
</script>

<h2>실습실 관리</h2>

<table border="1" cellpadding="6" style="border-collapse:collapse;margin-bottom:1rem">
  <tr><th>이름</th><th>행</th><th>열</th><th>설명</th><th></th></tr>
  {#each rooms as room}
    <tr>
      <td>{room.roomName}</td>
      <td>{room.rows}</td>
      <td>{room.cols}</td>
      <td>{room.description ?? '-'}</td>
      <td><button on:click={() => del(room.id)}>삭제</button></td>
    </tr>
  {/each}
</table>

<h3>새 실습실 추가</h3>
<form on:submit|preventDefault={create} style="display:flex;gap:0.5rem;flex-wrap:wrap;align-items:flex-end">
  <label>이름 <input bind:value={name} required /></label>
  <label>행 <input type="number" bind:value={rows} min="1" max="20" style="width:60px" /></label>
  <label>열 <input type="number" bind:value={cols} min="1" max="20" style="width:60px" /></label>
  <label>설명 <input bind:value={desc} /></label>
  <button type="submit">추가</button>
</form>
{#if message}<p style="color:green">{message}</p>{/if}