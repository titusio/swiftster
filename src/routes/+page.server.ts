import { listTracks } from '$lib/server/media';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async () => {
	return { tracks: await listTracks() };
};
