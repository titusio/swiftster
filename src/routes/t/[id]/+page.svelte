<script lang="ts">
	import { onMount } from 'svelte';
	import type { PageData } from './$types';

	type Answer = { title: string; artist: string; album: string };

	let { data }: { data: PageData } = $props();

	let audio = $state<HTMLAudioElement>();
	let blocked = $state(false);
	let answer = $state<Answer | null>(null);
	let revealing = $state(false);
	let failed = $state('');

	onMount(() => {
		// The lock screen and the system media controls read this. Without it the
		// browser falls back to the file's own tags, which hands over the answer.
		if ('mediaSession' in navigator) {
			navigator.mediaSession.metadata = new MediaMetadata({ title: 'Guess the track' });
		}

		void play();
	});

	async function play() {
		if (!audio) return;

		try {
			await audio.play();
			blocked = false;
		} catch {
			// Autoplay survives a scan made in the app, which carries the tap that
			// started the camera, but not a cold open from the phone's camera app.
			blocked = true;
		}
	}

	async function reveal() {
		revealing = true;
		failed = '';

		try {
			const response = await fetch(`/api/tracks/${data.id}`);
			if (!response.ok) throw new Error(String(response.status));
			answer = await response.json();
		} catch {
			failed = 'Could not load the answer — try again.';
		} finally {
			revealing = false;
		}
	}
</script>

<svelte:head><title>swiftster</title></svelte:head>

<div class="mx-auto flex min-h-dvh max-w-md flex-col gap-8 p-6">
	<div class="flex flex-1 flex-col items-center justify-center gap-6 text-center">
		{#if answer}
			<div>
				<h1 class="text-2xl font-semibold text-balance">{answer.title}</h1>
				<p class="mt-2 text-neutral-500">{answer.artist} · {answer.album}</p>
			</div>
		{:else}
			<div>
				<h1 class="text-2xl font-semibold">Guess the track</h1>
				<p class="mt-2 text-neutral-500">Listen, call it out, then reveal.</p>
			</div>
		{/if}

		{#if blocked}
			<button
				type="button"
				class="rounded-full bg-neutral-900 px-6 py-3 font-medium text-white"
				onclick={play}
			>
				Tap to play
			</button>
		{/if}
	</div>

	<div class="space-y-4">
		<audio bind:this={audio} src="/api/tracks/{data.id}/stream" class="w-full" controls></audio>

		{#if !answer}
			<button
				type="button"
				class="w-full rounded-md bg-neutral-900 px-4 py-3 font-medium text-white disabled:opacity-60"
				onclick={reveal}
				disabled={revealing}
			>
				{revealing ? 'Revealing…' : 'Reveal'}
			</button>
		{/if}

		{#if failed}
			<p class="text-center text-sm text-red-600">{failed}</p>
		{/if}

		<a
			href="/"
			class="block rounded-md border border-neutral-300 px-4 py-3 text-center font-medium"
		>
			Scan another
		</a>
	</div>
</div>
