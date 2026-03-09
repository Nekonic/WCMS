<script lang="ts">
  import { onMount } from 'svelte'
  import { api } from '$lib/api.js'

  let rooms: any[] = []
  let selectedRoom = ''
  let seats: any[] = []
  let layout: any = null
  let loading = false
  let cmdModal: any = null

  onMount(async () => {
    rooms = await api.rooms()
    if (rooms.length) loadRoom(rooms[0].roomName)
  })

  async function loadRoom(name: string) {
    selectedRoom = name
    loading = true
    const data = await api.roomLayout(name)
    layout = data.room
    seats = data.seats
    loading = false
  }

  async function sendCmd(pc: any, type: string) {
    await api.sendCommand(pc.pcId, { command_type: type })
    cmdModal = null
  }
</script>

<div style="display:flex;gap:0.5rem;margin-bottom:1rem;align-items:center">
  {#each rooms as room}
    <button on:click={() => loadRoom(room.roomName)}
            style={room.roomName === selectedRoom ? 'font-weight:bold' : ''}>
      {room.roomName}
    </button>
  {/each}
  <button on:click={() => { if (selectedRoom) loadRoom(selectedRoom) }}>새로고침</button>
</div>

{#if loading}
  <p>로딩 중...</p>
{:else if layout}
  <div style="display:grid;grid-template-columns:repeat({layout.cols}, 130px);gap:0.4rem">
    {#each Array(layout.rows) as _, ri}
      {#each Array(layout.cols) as _, ci}
        {@const seat = seats.find(s => s.row === ri+1 && s.col === ci+1)}
        {#if seat?.pcId}
          <button style="border:1px solid #ccc;padding:0.5rem;border-radius:4px;cursor:pointer;background:{seat.isOnline ? '#e8f5e9' : '#fafafa'};text-align:left;width:100%"
               on:click={() => cmdModal = seat}>
            <div style="font-size:0.75rem;color:{seat.isOnline ? 'green' : 'gray'}">{seat.isOnline ? '온라인' : '오프라인'}</div>
            <div style="font-size:0.85rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{seat.hostname ?? '?'}</div>
            <div style="font-size:0.7rem;color:#888">{ri+1}-{ci+1}</div>
          </button>
        {:else}
          <div style="border:1px dashed #eee;padding:0.5rem;border-radius:4px;background:#fafafa">
            <div style="font-size:0.7rem;color:#ccc">{ri+1}-{ci+1}</div>
          </div>
        {/if}
      {/each}
    {/each}
  </div>
{/if}

{#if cmdModal}
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.4);display:flex;align-items:center;justify-content:center"
       role="presentation"
       on:click|self={() => cmdModal = null}
       on:keydown|self={(e) => e.key === 'Escape' && (cmdModal = null)}>
    <div style="background:white;padding:1.5rem;border-radius:8px;min-width:280px">
      <h3 style="margin-top:0">{cmdModal.hostname}</h3>
      <div style="display:flex;flex-direction:column;gap:0.5rem">
        <button on:click={() => sendCmd(cmdModal, 'shutdown')}>종료</button>
        <button on:click={() => sendCmd(cmdModal, 'restart')}>재시작</button>
      </div>
      <button on:click={() => cmdModal = null} style="margin-top:0.75rem">닫기</button>
    </div>
  </div>
{/if}