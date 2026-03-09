<script lang="ts">
  import { onMount } from 'svelte'
  import { api } from '$lib/api.js'

  let rooms: any[] = []
  let selectedRoom = ''
  let layout: any = null
  let pcs: any[] = []
  let seats: { row: number; col: number; pc_id: number | null }[] = []
  let saved = false

  onMount(async () => {
    [rooms, pcs] = await Promise.all([api.rooms(), api.pcs()])
    if (rooms.length) loadRoom(rooms[0].roomName)
  })

  async function loadRoom(name: string) {
    selectedRoom = name
    const data = await api.roomLayout(name)
    layout = data.room
    seats = []
    for (let r = 1; r <= layout.rows; r++) {
      for (let c = 1; c <= layout.cols; c++) {
        const found = data.seats.find((s: any) => s.row === r && s.col === c)
        seats.push({ row: r, col: c, pc_id: found?.pcId ?? null })
      }
    }
    seats = [...seats]
    saved = false
  }

  async function save() {
    await api.saveLayout(selectedRoom, seats)
    saved = true
  }

  function setPcId(r: number, c: number, val: string) {
    const seat = seats.find(s => s.row === r && s.col === c)
    if (seat) seat.pc_id = val ? Number(val) : null
    seats = [...seats]
  }
</script>

<h2>좌석 배치 편집기</h2>

<div style="display:flex;gap:0.5rem;margin-bottom:1rem;align-items:center">
  {#each rooms as room}
    <button on:click={() => loadRoom(room.roomName)}
            style={room.roomName === selectedRoom ? 'font-weight:bold' : ''}>
      {room.roomName}
    </button>
  {/each}
</div>

{#if layout}
  <div style="overflow-x:auto">
    <table style="border-collapse:collapse">
      {#each Array(layout.rows) as _, ri}
        <tr>
          {#each Array(layout.cols) as _, ci}
            {@const seat = seats.find(s => s.row === ri+1 && s.col === ci+1)}
            <td style="border:1px solid #ccc;padding:4px">
              <select value={seat?.pc_id ?? ''} on:change={e => setPcId(ri+1, ci+1, (e.target as any).value)}
                      style="width:130px;font-size:0.75rem">
                <option value="">비어있음</option>
                {#each pcs as pc}
                  <option value={pc.id}>{pc.hostname}</option>
                {/each}
              </select>
              <div style="font-size:0.65rem;color:#888;text-align:center">{ri+1}-{ci+1}</div>
            </td>
          {/each}
        </tr>
      {/each}
    </table>
  </div>
  <div style="margin-top:1rem">
    <button on:click={save}>저장</button>
    {#if saved}<span style="color:green;margin-left:0.5rem">저장됨</span>{/if}
  </div>
{/if}