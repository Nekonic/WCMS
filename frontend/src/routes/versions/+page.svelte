<script lang="ts">
  import { onMount } from 'svelte'
  import { api } from '$lib/api.js'

  let versions: any[] = []

  onMount(async () => { versions = await api.versions() })

  async function del(id: number) {
    if (!confirm('삭제하시겠습니까?')) return
    await api.deleteVersion(id)
    versions = await api.versions()
  }

  function fmt(iso: string) {
    return new Date(iso).toLocaleString('ko-KR')
  }
</script>

<h2>클라이언트 버전</h2>

<table border="1" cellpadding="6" style="border-collapse:collapse">
  <tr><th>버전</th><th>다운로드 URL</th><th>변경사항</th><th>등록일</th><th></th></tr>
  {#each versions as v}
    <tr>
      <td>{v.version}</td>
      <td>{v.downloadUrl ?? '-'}</td>
      <td>{v.changelog ?? '-'}</td>
      <td>{fmt(v.releasedAt)}</td>
      <td><button on:click={() => del(v.id)}>삭제</button></td>
    </tr>
  {/each}
</table>