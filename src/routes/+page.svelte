<script lang="ts">
  let { trackId }: { trackId: string } = $props();
  let audio = $state<HTMLAudioElement>();
</script>

<h1>Welcome to SvelteKit</h1>
<p>
  Visit <a href="https://svelte.dev/docs/kit">svelte.dev/docs/kit</a> to read the
  documentation
</p>

<audio
  bind:this={audio}
  src="/api/tracks/179708898/stream"
  controls
  preload="metadata"
></audio>
