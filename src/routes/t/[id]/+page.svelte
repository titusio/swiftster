<script lang="ts">
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
</script>

<svelte:head><title>{data.track.title} · {data.track.artist}</title></svelte:head>

<div class="mx-auto max-w-md space-y-6 p-6">
	<a href="/" class="text-sm text-neutral-500 hover:text-neutral-800">← Scan</a>

	<div>
		<h1 class="text-2xl font-semibold">{data.track.title}</h1>
		<p class="text-neutral-500">{data.track.artist} · {data.track.album}</p>
	</div>

	<!--
		autoplay only survives if the browser counts the scan as a user gesture,
		which it does after a tap in the app but not after a cold camera-app open.
		The controls are the fallback, so keep them.
	-->
	<audio
		src="/api/tracks/{data.track.id}/stream"
		class="w-full"
		controls
		autoplay
		preload="metadata"
	></audio>

	<a
		href="/"
		class="inline-block rounded-md bg-neutral-900 px-3 py-1.5 text-sm font-medium text-white"
	>
		Scan another
	</a>
</div>
