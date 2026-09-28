<script lang="ts">
	type Props = {
		class?: string;
	};

	let { class: className = '' }: Props = $props();
</script>

<!--
	The same mark as static/icon.svg, drawn inline so it takes currentColor. The
	file version carries a prefers-color-scheme rule for the browser's chrome,
	which would turn it near-white on this very white page.
-->
<svg viewBox="0 0 32 32" fill="currentColor" aria-hidden="true" class={className}>
	<path fill-rule="evenodd" d="M2 2h13v13H2zM5 5v7h7V5z" />
	<rect x="6.5" y="6.5" width="4" height="4" />
	<path fill-rule="evenodd" d="M17 2h13v13H17zM20 5v7h7V5z" />
	<rect x="21.5" y="6.5" width="4" height="4" />
	<path fill-rule="evenodd" d="M2 17h13v13H2zM5 20v7h7v-7z" />
	<rect x="6.5" y="21.5" width="4" height="4" />
	<path d="M20 18.5 28.5 23.5 20 28.5z" />
</svg>
