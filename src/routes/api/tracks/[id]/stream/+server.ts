import { createReadStream } from 'node:fs';
import { Readable } from 'node:stream';
import { error } from '@sveltejs/kit';
import { getTrack, trackSize } from '$lib/server/media';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ params, request }) => {
	const track = await getTrack(params.id);
	if (!track) error(404, 'Track not found');

	const size = await trackSize(track);
	const range = request.headers.get('range');

	const headers = new Headers({
		'Content-Type': track.mimeType,
		'Accept-Ranges': 'bytes',
		'Cache-Control': 'private, max-age=3600'
	});

	// No Range header: send the whole file.
	if (!range) {
		headers.set('Content-Length', String(size));
		return new Response(Readable.toWeb(createReadStream(track.path)) as ReadableStream, {
			status: 200,
			headers
		});
	}

	const match = /^bytes=(\d*)-(\d*)$/.exec(range.trim());
	if (!match) {
		return new Response(null, {
			status: 416,
			headers: { 'Content-Range': `bytes */${size}` }
		});
	}

	const start = match[1] ? Number(match[1]) : 0;
	const end = match[2] ? Math.min(Number(match[2]), size - 1) : size - 1;

	if (!Number.isFinite(start) || !Number.isFinite(end) || start > end || start >= size) {
		return new Response(null, {
			status: 416,
			headers: { 'Content-Range': `bytes */${size}` }
		});
	}

	headers.set('Content-Range', `bytes ${start}-${end}/${size}`);
	headers.set('Content-Length', String(end - start + 1));

	return new Response(
		Readable.toWeb(createReadStream(track.path, { start, end })) as ReadableStream,
		{ status: 206, headers }
	);
};
