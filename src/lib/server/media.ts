import { readFile, stat } from 'node:fs/promises';
import { extname, isAbsolute, join, resolve } from 'node:path';
import { env } from '$env/dynamic/private';

export type Track = {
	id: string;
	title: string;
	artist: string;
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

/** The index written by `scripts/index-music.py`. */
function indexFile(): string {
	return env.MEDIA_INDEX || join(mediaDir(), 'songs.json');
}

/** One entry of songs.json, before we trust any of it. */
type Entry = Partial<Record<keyof Omit<Track, 'mimeType'>, unknown>>;

let index: Map<string, Track> | null = null;

async function load(): Promise<Map<string, Track>> {
	const file = indexFile();

	let entries: unknown;
	try {
		entries = JSON.parse(await readFile(file, 'utf-8'));
	} catch (cause) {
		throw new Error(`could not read the music index at ${file}`, { cause });
	}

	if (!Array.isArray(entries)) throw new Error(`${file} is not a JSON array`);

	const built = new Map<string, Track>();

	for (const entry of entries as Entry[]) {
		const { id, title, artist, album, path } = entry;
		if (typeof id !== 'string' || typeof path !== 'string') continue;

		const mimeType = MIME_TYPES[extname(path).toLowerCase()];
		if (!mimeType) continue;

		built.set(id, {
			id,
			title: typeof title === 'string' ? title : id,
			artist: typeof artist === 'string' ? artist : '',
			album: typeof album === 'string' ? album : '',
			// The indexer may write either absolute paths or ones relative to the
			// library root, depending on where it was run from.
			path: isAbsolute(path) ? path : resolve(mediaDir(), path),
			mimeType
		});
	}

	return built;
}

export async function getIndex(): Promise<Map<string, Track>> {
	if (index) return index;
	index = await load();
	return index;
}

/** Drop the cached index so the next request re-reads songs.json. */
export function invalidateIndex(): void {
	index = null;
}

export async function getTrack(id: string): Promise<Track | undefined> {
	return (await getIndex()).get(id);
}

export async function listTracks(): Promise<Omit<Track, 'path'>[]> {
	return [...(await getIndex()).values()]
		.map(({ path: _path, ...track }) => track)
		.sort(
			(a, b) =>
				a.artist.localeCompare(b.artist) ||
				a.album.localeCompare(b.album) ||
				a.title.localeCompare(b.title)
		);
}

export async function trackSize(track: Track): Promise<number> {
	return (await stat(track.path)).size;
}
