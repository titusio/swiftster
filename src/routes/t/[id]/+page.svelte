<script lang="ts">
	import { onMount } from 'svelte';
	import { clip } from '$lib/clip.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	let audio = $state<HTMLAudioElement>();
	let paused = $state(true);
	let ended = $state(false);

	// Reaching the end leaves `paused` false in some browsers, so the button has
	// to look at both to know whether anything is actually coming out.
	let playing = $derived(!paused && !ended);

	// Where the current stretch of playback stops, in media time. Media time
	// rather than wall-clock so buffering eats into the wait, not into the clip.
	// Only the opening stretch is cut short: pressing play is asking to hear
	// more, so a resume runs to the end of the track.
	let deadline = Infinity;
	let opened = false;
	let limited = false;
	let frame: number | null = null;

	onMount(() => {
		// The lock screen and the system media controls read this. Without it the
		// browser falls back to the file's own tags, which hands over the answer.
		if ('mediaSession' in navigator) {
			navigator.mediaSession.metadata = new MediaMetadata({ title: 'Guess the track' });
		}

		void play();

		return () => {
			if (frame !== null) cancelAnimationFrame(frame);
		};
	});

	$effect(() => {
		// Changing the length mid-clip re-arms against where we are now. Computed
		// up front so the effect tracks the setting; `audio.paused` is read off the
		// element, which does not make it a dependency.
		const target = arm(audio?.currentTime ?? 0);
		if (limited && audio && !audio.paused) deadline = target;
	});

	function arm(from: number): number {
		return clip.seconds ? from + clip.seconds : Infinity;
	}

	/**
	 * timeupdate only fires about four times a second, which is too coarse to cut
	 * a one-second clip, so watch the clock per frame instead.
	 */
	function watch() {
		if (!audio || audio.paused) {
			frame = null;
			return;
		}

		if (audio.currentTime >= deadline) {
			audio.pause();
			frame = null;
			return;
		}

		frame = requestAnimationFrame(watch);
	}

	async function play() {
		if (!audio) return;

		if (ended) audio.currentTime = 0;
		limited = !opened;
		deadline = limited ? arm(audio.currentTime) : Infinity;

		try {
			await audio.play();
		} catch {
			// Autoplay survives a scan made in the app, which carries the tap that
			// started the camera, but not a cold open from the phone's camera app.
			// That lands here still unopened, so the tap gets the clip instead.
			return;
		}

		opened = true;
		if (frame === null) frame = requestAnimationFrame(watch);
	}

	function toggle() {
		if (playing) audio?.pause();
		else void play();
	}
</script>

<svelte:head><title>swiftster</title></svelte:head>

<audio bind:this={audio} bind:paused bind:ended src="/api/tracks/{data.id}/stream" class="hidden"
></audio>

<div class="flex flex-1 flex-col items-center justify-center gap-10 text-center">
	<div>
		<h1 class="text-2xl font-semibold">Guess the track</h1>
		<p class="mt-2 text-neutral-500">Listen, call it out, then turn the card over.</p>
	</div>

	<button
		type="button"
		class="grid h-36 w-36 place-items-center rounded-full bg-neutral-900 text-white active:scale-95"
		aria-label={playing ? 'Pause' : 'Play'}
		onclick={toggle}
	>
		{#if playing}
			<svg class="h-16 w-16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
				<path d="M6 5h4v14H6zM14 5h4v14h-4z" />
			</svg>
		{:else}
			<!-- A triangle sits visually left of centre in a circle; nudge it back. -->
			<svg
				class="h-16 w-16 translate-x-1"
				viewBox="0 0 24 24"
				fill="currentColor"
				aria-hidden="true"
			>
				<path d="M8 5v14l11-7z" />
			</svg>
		{/if}
	</button>
</div>

<a href="/" class="block rounded-md border border-neutral-300 px-4 py-3 text-center font-medium">
	Scan another
</a>
