<script lang="ts">
	import { CLIPS, clip, remember } from '$lib/clip.svelte';
</script>

<!--
	iOS draws its chevron over the label rather than reserving room for it, so the
	right padding is the fix. Suppressing the native arrow and drawing our own is
	the other option, but `appearance: none` does not reliably take there and you
	end up with both.
-->
<select
	bind:value={clip.seconds}
	onchange={remember}
	aria-label="How much to play at a time"
	class="rounded-md border border-neutral-300 bg-white py-1 pr-8 pl-2 text-sm"
>
	{#each CLIPS as { seconds, label } (seconds)}
		<option value={seconds}>{label}</option>
	{/each}
</select>
