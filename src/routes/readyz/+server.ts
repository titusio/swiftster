import { access, constants } from 'node:fs/promises';
import { json } from '@sveltejs/kit';
import { getIndex } from '$lib/server/media';
import type { RequestHandler } from './$types';

const headers = { 'cache-control': 'no-store' };

function unready(reason: string, cause?: unknown): Response {
	// The cause names host paths, so it goes to the log and not to whoever asked.
	console.error(`not ready: ${reason}`, cause ?? '');
	return json({ status: 'unready', reason }, { status: 503, headers });
}

/**
 * Readiness: a scanned card would play. That needs an index with something in
 * it, and a library its paths actually resolve into — a MEDIA_DIR that does not
 * match the one the index was built against loads fine and then 404s every
 * stream, so one track's file is checked as well as the index.
 */
export const GET: RequestHandler = async () => {
	let index;
	try {
		index = await getIndex();
	} catch (cause) {
		return unready('the music index could not be loaded', cause);
	}

	const [track] = index.values();
	if (!track) return unready('the music index has no playable tracks');

	try {
		await access(track.path, constants.R_OK);
	} catch (cause) {
		return unready('the music library is not readable', cause);
	}

	return json({ status: 'ready', tracks: index.size }, { headers });
};
