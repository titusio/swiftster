import { error, json } from '@sveltejs/kit';
import { getTrack } from '$lib/server/media';
import type { RequestHandler } from './$types';

/** The answer to a round, fetched once the player has given up guessing. */
export const GET: RequestHandler = async ({ params }) => {
	const track = await getTrack(params.id);
	if (!track) error(404, 'Track not found');

	const { path: _path, ...rest } = track;
	return json(rest);
};
