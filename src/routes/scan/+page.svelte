<script lang="ts">
	import QrScanner from '$lib/components/QrScanner.svelte';

	let results = $state<{ value: string; at: string }[]>([]);

	function onscan(value: string) {
		results = [{ value, at: new Date().toLocaleTimeString() }, ...results].slice(0, 20);
	}
</script>

<div class="mx-auto max-w-md space-y-6 p-6">
	<h1 class="text-2xl font-semibold">Scan a QR code</h1>

	<QrScanner {onscan} class="aspect-square w-full" />

	{#if results.length}
		<ul class="space-y-2">
			{#each results as result (result.at + result.value)}
				<li class="rounded-md border border-neutral-300 p-3 text-sm">
					<span class="block font-mono break-all">{result.value}</span>
					<span class="text-xs text-neutral-500">{result.at}</span>
				</li>
			{/each}
		</ul>
	{:else}
		<p class="text-sm text-neutral-500">Point the camera at a QR code.</p>
	{/if}
</div>
