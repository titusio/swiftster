import { text } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

// Liveness: the process is up and answering. It looks at nothing else on
// purpose, so a library that has gone missing makes the server unready rather
// than dead, and nothing restarts it in a loop over a mount it cannot fix.
export const GET: RequestHandler = () => {
	return text('ok', { headers: { 'cache-control': 'no-store' } });
};
