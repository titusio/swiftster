/**
 * What a track QR code contains.
 *
 * Codes get printed and stuck to physical things, so the payload has to outlive
 * route changes: keep the path short and treat it as a permalink, not as
 * wherever the player happens to live today.
 */
export const TRACK_PATH = '/t';

/** Ids come from the library filenames, so keep this in step with index-music.py. */
const ID = /^[A-Za-z0-9_-]+$/;

/** The URL to encode. `origin` comes from PUBLIC_ORIGIN at generation time. */
export function trackUrl(id: string, origin = ''): string {
	return `${origin}${TRACK_PATH}/${encodeURIComponent(id)}`;
}

/**
 * Turn a scanned payload back into a track id, or null if it isn't one of ours.
 *
 * Accepts a bare id as well as the full URL, so codes printed against an origin
 * that has since moved — or written by hand — keep working with the in-app
 * scanner. Only the URL form does anything in a phone's camera app.
 */
export function parseTrackCode(value: string): string | null {
	const trimmed = value.trim();
	if (!trimmed) return null;
	if (ID.test(trimmed)) return trimmed;

	let url: URL;
	try {
		url = new URL(trimmed);
	} catch {
		return null;
	}

	const segments = url.pathname.split('/').filter(Boolean);
	if (segments.length !== 2 || `/${segments[0]}` !== TRACK_PATH) return null;

	const id = decodeURIComponent(segments[1]);
	return ID.test(id) ? id : null;
}
