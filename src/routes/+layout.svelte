<script lang="ts">
	import './layout.css';
	import { version } from '$app/environment';
	import ClipPicker from '$lib/components/ClipPicker.svelte';
	import RandomToggle from '$lib/components/RandomToggle.svelte';
	import type { Snippet } from 'svelte';
	import type { LayoutData } from './$types';

	let { data, children }: { data: LayoutData; children: Snippet } = $props();
</script>

<svelte:head>
	<title>{data.name}</title>
	<!-- iOS reads the home-screen label from here in preference to the manifest. -->
	<meta name="apple-mobile-web-app-title" content={data.name} />
</svelte:head>

<!--
	The page frame lives here so the round settings keep their corner across a
	scan. Pages render straight into the column: a section marked flex-1 fills it.
-->
<div class="mx-auto flex min-h-dvh max-w-md flex-col gap-6 p-6">
	<header class="flex flex-wrap items-center justify-end gap-x-4 gap-y-2">
		<!--
			mr-auto rather than justify-between: a name too long for the row wraps the
			settings onto their own line, where justify-end still holds them.
		-->
		<a href="/" class="mr-auto text-lg font-semibold">{data.name}</a>
		<RandomToggle />
		<ClipPicker />
	</header>

	{@render children()}

	<!-- mt-auto so the footer sits at the bottom of a short page too. -->
	<footer class="mt-auto flex items-center justify-center gap-2 text-xs text-neutral-500">
		<span>
			Powered by
			<a href="https://github.com/titusio/swiftster" class="underline underline-offset-2">swiftster</a>
		</span>
		<span aria-hidden="true">·</span>
		<span>{version}</span>
	</footer>
</div>
