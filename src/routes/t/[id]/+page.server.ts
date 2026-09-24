import { error } from '@sveltejs/kit';
import { getTrack } from '$lib/server/media';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params }) => {
	// Only the id. The title is the answer, and anything returned here is in the
	// page source before the player has guessed, so the metadata stays on the
	// server until the reveal asks for it.
	if (!(await getTrack(params.id))) error(404, 'Track not found');

	return { id: params.id };
};
