import { error } from '@sveltejs/kit';
import { getTrack } from '$lib/server/media';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params }) => {
	const track = await getTrack(params.id);
	if (!track) error(404, 'Track not found');

	// The on-disk path stays on the server; the client streams by id.
	const { path: _path, ...rest } = track;
	return { track: rest };
};
