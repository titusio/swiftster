import { json } from '@sveltejs/kit';
import { listTracks } from '$lib/server/media';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async () => {
	return json(await listTracks());
};
