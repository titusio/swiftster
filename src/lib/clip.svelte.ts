import { browser } from '$app/environment';

/** How much of a track a round plays before stopping. 0 means the whole thing. */
export const CLIPS = [
	{ seconds: 0, label: 'Full song' },
	{ seconds: 1, label: '1 second' },
	{ seconds: 5, label: '5 seconds' },
	{ seconds: 10, label: '10 seconds' },
	{ seconds: 30, label: '30 seconds' }
];

const STORAGE_KEY = 'swiftster:clip-seconds';

function stored(): number {
	if (!browser) return 0;

	try {
		const value = Number(localStorage.getItem(STORAGE_KEY));
		return CLIPS.some((clip) => clip.seconds === value) ? value : 0;
	} catch {
		// Private mode and blocked site data both throw; the default is fine.
		return 0;
	}
}

/**
 * The difficulty setting, shared between the scanner and the round: each scan
 * is a fresh page load, so a value living in either one would reset every turn.
 */
export const clip = $state({ seconds: stored() });

export function remember(): void {
	try {
		localStorage.setItem(STORAGE_KEY, String(clip.seconds));
	} catch {
		// Forgetting the setting is not worth interrupting the game over.
	}
}
