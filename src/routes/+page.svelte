<script lang="ts">
	import { goto } from '$app/navigation';
	import QrScanner from '$lib/components/QrScanner.svelte';
	import { parseTrackCode } from '$lib/track-code';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	let rejected = $state('');

	function onscan(value: string) {
		const id = parseTrackCode(value);
		if (!id) {
			rejected = value;
			return;
		}

		rejected = '';
		// Navigating away unmounts the scanner, which releases the camera.
		goto(`/t/${id}`);
	}
</script>

<svelte:head><title>swiftster</title></svelte:head>

<div class="mx-auto max-w-md space-y-6 p-6">
	<h1 class="text-2xl font-semibold">Scan a track</h1>

	<QrScanner {onscan} class="aspect-square w-full" />

	{#if rejected}
		<p class="text-sm text-red-600">
			That code isn’t a track: <span class="font-mono break-all">{rejected}</span>
		</p>
	{:else}
		<p class="text-sm text-neutral-500">Point the camera at a track code.</p>
	{/if}

	{#if data.tracks.length}
		<div class="space-y-2">
			<h2 class="text-sm font-medium text-neutral-500">Library</h2>
			<ul class="divide-y divide-neutral-200">
				{#each data.tracks as track (track.id)}
					<li>
						<a href="/t/{track.id}" class="block py-3 hover:bg-neutral-50">
							<span class="block">{track.title}</span>
							<span class="block text-sm text-neutral-500">{track.artist} · {track.album}</span>
						</a>
					</li>
				{/each}
			</ul>
		</div>
	{:else}
		<p class="text-sm text-neutral-500">
			No tracks indexed yet — run <code class="font-mono">just index</code>.
		</p>
	{/if}
</div>
