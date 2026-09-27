<script lang="ts">
	import { clip, remember } from '$lib/clip.svelte';

	function toggle() {
		clip.random = !clip.random;
		remember();
	}
</script>

<!--
	A switch rather than a checkbox: it is the one setting that is simply on or
	off, and the knob says which way it is from across the table. The label text
	is the accessible name, so the role and the state are all it needs on top.
-->
<button
	type="button"
	role="switch"
	aria-checked={clip.random}
	onclick={toggle}
	class="flex items-center gap-2 rounded-md text-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-neutral-900"
>
	Random start

	<!--
		The knob is pinned rather than left where it falls: an absolute box with no
		`left` starts from its static position, which the whitespace in the markup
		moves, and it slides off the end of the track.
	-->
	<span
		class="relative h-5 w-9 rounded-full transition-colors {clip.random
			? 'bg-neutral-900'
			: 'bg-neutral-300'}"
	>
		<span
			class="absolute top-0.5 left-0.5 h-4 w-4 rounded-full bg-white shadow-sm transition-transform {clip.random
				? 'translate-x-4'
				: 'translate-x-0'}"
		></span>
	</span>
</button>
