import tailwindcss from '@tailwindcss/vite';
import adapter from '@sveltejs/adapter-node';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig, loadEnv } from 'vite';

/**
 * Hosts Vite will answer to, from `ALLOWED_HOSTS` (comma-separated).
 * `true` or `*` disables the check entirely — convenient on a trusted LAN,
 * but it drops Vite's DNS-rebinding protection, so don't use it on an
 * untrusted network.
 */
function allowedHosts(value: string | undefined): string[] | true {
	const entries =
		value
			?.split(',')
			.map((host) => host.trim())
			.filter(Boolean) ?? [];

	if (entries.some((host) => host === 'true' || host === '*')) return true;
	return entries;
}

export default defineConfig(({ mode }) => {
	// '' prefix: load every key, not just VITE_. This file runs in Node only,
	// so nothing here is exposed to the client.
	const env = loadEnv(mode, process.cwd(), '');
	const hosts = allowedHosts(env.ALLOWED_HOSTS);

	return {
		plugins: [
			tailwindcss(),
			sveltekit({
				compilerOptions: {
					// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
					runes: ({ filename }) =>
						filename.split(/[/\\]/).includes('node_modules') ? undefined : true
				},

				// A plain Node server, so the build runs anywhere: the container, or
				// `node build` on the host. Its PORT, HOST and ORIGIN come from the
				// environment at run time — see the Dockerfile and compose.yaml.
				adapter: adapter()
			})
		],
		server: { allowedHosts: hosts },
		preview: { allowedHosts: hosts }
	};
});
