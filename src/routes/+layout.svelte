<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import ClipPicker from '$lib/components/ClipPicker.svelte';

	let { children } = $props();
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>

<!--
	The page frame lives here so the clip picker keeps its corner across a scan.
	Pages render straight into the column: a section marked flex-1 fills it.
-->
<div class="mx-auto flex min-h-dvh max-w-md flex-col gap-6 p-6">
	<header class="flex justify-end">
		<ClipPicker />
	</header>

	{@render children()}
</div>
