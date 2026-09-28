import { json } from '@sveltejs/kit';
import { appName } from '$lib/server/name';
import type { RequestHandler } from './$types';

// A route rather than a file in static/, so the home-screen label is the name
// this server was given like everything else.
export const GET: RequestHandler = () => {
	const name = appName();

	return json(
		{
			name,
			short_name: name,
			description: 'Scan a card, hear the track.',
			start_url: '/',
			scope: '/',
			display: 'standalone',
			orientation: 'portrait',
			background_color: '#ffffff',
			theme_color: '#ffffff',
			icons: [
				{ src: '/icon.svg', type: 'image/svg+xml', sizes: 'any' },
				{ src: '/icon-192.png', type: 'image/png', sizes: '192x192' },
				{ src: '/icon-512.png', type: 'image/png', sizes: '512x512' },
				{
					src: '/icon-maskable-512.png',
					type: 'image/png',
					sizes: '512x512',
					purpose: 'maskable'
				}
			]
		},
		{ headers: { 'content-type': 'application/manifest+json' } }
	);
};
