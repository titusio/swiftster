<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { createDetector, type QrDetector } from '$lib/qr';

	type Status = 'idle' | 'starting' | 'scanning' | 'error';

	type Props = {
		/** Called for each accepted scan. Repeats within `cooldownMs` are suppressed. */
		onscan: (value: string) => void;
		/** How long the same value stays suppressed after a hit. */
		cooldownMs?: number;
		class?: string;
	};

	let { onscan, cooldownMs = 1500, class: className = '' }: Props = $props();

	let video = $state<HTMLVideoElement>();
	let status = $state<Status>('idle');
	let errorMessage = $state('');

	let stream: MediaStream | null = null;
	let detector: QrDetector | null = null;

	// The detect() call is wasm-backed and can outlast a frame interval, so we
	// skip frames while one is in flight rather than queueing them up.
	let busy = false;
	let stopped = true;
	let frameHandle: number | null = null;
	let usingVideoCallback = false;
	let lastValue = '';
	let lastAt = 0;

	function describe(err: unknown): string {
		if (err instanceof DOMException) {
			switch (err.name) {
				case 'NotAllowedError':
					return 'Camera access was denied. Allow it in your browser’s site settings, then retry.';
				case 'NotFoundError':
					return 'No camera found on this device.';
				case 'NotReadableError':
					return 'The camera is already in use by another application.';
				case 'OverconstrainedError':
					return 'No camera matched the requested constraints.';
			}
		}
		return err instanceof Error ? err.message : 'Could not start the camera.';
	}

	function queueFrame() {
		if (stopped || !video) return;

		if ('requestVideoFrameCallback' in video) {
			usingVideoCallback = true;
			frameHandle = video.requestVideoFrameCallback(() => void tick());
		} else {
			usingVideoCallback = false;
			frameHandle = requestAnimationFrame(() => void tick());
		}
	}

	function cancelFrame() {
		if (frameHandle === null) return;

		if (usingVideoCallback) video?.cancelVideoFrameCallback(frameHandle);
		else cancelAnimationFrame(frameHandle);

		frameHandle = null;
	}

	function emit(value: string) {
		const now = performance.now();
		if (value === lastValue && now - lastAt < cooldownMs) return;

		lastValue = value;
		lastAt = now;
		onscan(value);
	}

	async function tick() {
		if (stopped || !video || !detector) return;

		if (!busy && video.readyState >= video.HAVE_CURRENT_DATA) {
			busy = true;
			try {
				const [first] = await detector.detect(video);
				if (first?.rawValue) emit(first.rawValue);
			} catch {
				// A single frame failing to decode is normal; keep scanning.
			} finally {
				busy = false;
			}
		}

		queueFrame();
	}

	export async function start() {
		if (status === 'starting' || status === 'scanning') return;

		status = 'starting';
		errorMessage = '';
		stopped = false;

		try {
			if (!navigator.mediaDevices?.getUserMedia) {
				// getUserMedia is only exposed in a secure context.
				throw new Error(
					'Camera access needs HTTPS (or localhost). Open the app over a secure origin.'
				);
			}

			stream = await navigator.mediaDevices.getUserMedia({
				video: { facingMode: 'environment' },
				audio: false
			});

			// The component may have been torn down while we awaited permission.
			if (stopped) {
				stop();
				return;
			}
			if (!video) return;

			detector ??= createDetector();
			video.srcObject = stream;
			await video.play();

			status = 'scanning';
			queueFrame();
		} catch (err) {
			errorMessage = describe(err);
			status = 'error';
			stop();
		}
	}

	export function stop() {
		stopped = true;
		cancelFrame();

		stream?.getTracks().forEach((track) => track.stop());
		stream = null;

		if (video) video.srcObject = null;
		if (status === 'scanning' || status === 'starting') status = 'idle';
	}

	onMount(start);
	onDestroy(stop);
</script>

<div class={`relative overflow-hidden rounded-xl bg-black ${className}`}>
	<!-- svelte-ignore a11y_media_has_caption -->
	<video bind:this={video} class="h-full w-full object-cover" playsinline muted></video>

	{#if status === 'scanning'}
		<div class="pointer-events-none absolute inset-0 grid place-items-center">
			<div class="h-48 w-48 rounded-lg border-2 border-white/80 shadow-[0_0_0_100vmax_rgba(0,0,0,0.45)]"></div>
		</div>
	{/if}

	{#if status !== 'scanning'}
		<div class="absolute inset-0 grid place-items-center bg-black/70 p-6 text-center">
			{#if status === 'starting'}
				<p class="text-sm text-white/80">Starting camera…</p>
			{:else if status === 'error'}
				<div class="space-y-3">
					<p class="text-sm text-red-300">{errorMessage}</p>
					<button
						type="button"
						class="rounded-md bg-white px-3 py-1.5 text-sm font-medium text-black"
						onclick={start}
					>
						Retry
					</button>
				</div>
			{:else}
				<button
					type="button"
					class="rounded-md bg-white px-3 py-1.5 text-sm font-medium text-black"
					onclick={start}
				>
					Start camera
				</button>
			{/if}
		</div>
	{/if}
</div>
