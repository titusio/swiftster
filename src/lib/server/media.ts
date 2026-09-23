import { readdir, stat } from 'node:fs/promises';
import { extname, join } from 'node:path';
import { env } from '$env/dynamic/private';

export type Track = {
	id: string;
	title: string;
	album: string;
	path: string;
	mimeType: string;
};

const MIME_TYPES: Record<string, string> = {
	'.flac': 'audio/flac',
	'.mp3': 'audio/mpeg',
	'.m4a': 'audio/mp4',
	'.ogg': 'audio/ogg',
	'.opus': 'audio/ogg',
	'.wav': 'audio/wav'
};

function mediaDir(): string {
	if (!env.MEDIA_DIR) throw new Error('MEDIA_DIR is not set');
	return env.MEDIA_DIR;
}

/**
 * Filenames look like `10-The Way I Loved You (Taylor's Version)-179708914.flac`.
 * The trailing numeric segment is a stable id; fall back to the whole basename.
 */
function parseName(file: string): { id: string; title: string } {
	const base = file.slice(0, -extname(file).length);
	const match = /^(?:\d+-)?(.*)-(\d+)$/.exec(base);
	if (match) return { id: match[2], title: match[1] };
	return { id: base, title: base };
}

let index: Map<string, Track> | null = null;

async function scan(dir: string, album: string, into: Map<string, Track>): Promise<void> {
	const entries = await readdir(dir, { withFileTypes: true });

	for (const entry of entries) {
		const full = join(dir, entry.name);

		if (entry.isDirectory()) {
			await scan(full, entry.name, into);
			continue;
		}

		const mimeType = MIME_TYPES[extname(entry.name).toLowerCase()];
		if (!mimeType) continue;

		const { id, title } = parseName(entry.name);
		into.set(id, { id, title, album, path: full, mimeType });
	}
}

export async function getIndex(): Promise<Map<string, Track>> {
	if (index) return index;

	const built = new Map<string, Track>();
	await scan(mediaDir(), '', built);
	index = built;
	return index;
}

/** Drop the cached index so the next request re-scans the library. */
export function invalidateIndex(): void {
	index = null;
}

export async function getTrack(id: string): Promise<Track | undefined> {
	return (await getIndex()).get(id);
}

export async function listTracks(): Promise<Omit<Track, 'path'>[]> {
	return [...(await getIndex()).values()]
		.map(({ path: _path, ...track }) => track)
		.sort((a, b) => a.album.localeCompare(b.album) || a.title.localeCompare(b.title));
}

export async function trackSize(track: Track): Promise<number> {
	return (await stat(track.path)).size;
}
