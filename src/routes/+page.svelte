<script lang="ts">
	import { goto } from '$app/navigation';
	import QrScanner from '$lib/components/QrScanner.svelte';
	import { parseTrackCode } from '$lib/track-code';

	let rejected = $state('');

	function onscan(value: string) {
		const id = parseTrackCode(value);
		if (!id) {
			rejected = value;
			return;
		}

		rejected = '';
		// Navigating away unmounts the scanner, which releases the camera. It also
		// keeps the tap that started the camera in the same document, so the round
		// counts as user-initiated and the track is allowed to autoplay.
		goto(`/t/${id}`);
	}
</script>

<svelte:head><title>swiftster</title></svelte:head>

<div class="space-y-6">
	<div>
		<h1 class="text-2xl font-semibold">Scan a card</h1>
		<p class="mt-1 text-sm text-neutral-500">
			The track starts playing on its own. Name it, then turn the card over.
		</p>
	</div>

	<QrScanner {onscan} class="aspect-square w-full" />

	{#if rejected}
		<p class="text-sm text-red-600">
			That code isn’t a track: <span class="font-mono break-all">{rejected}</span>
		</p>
	{/if}
</div>
