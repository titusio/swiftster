import { browser } from '$app/environment';

/** How much of a track a round plays before stopping. 0 means the whole thing. */
export const CLIPS = [
	{ seconds: 0, label: 'Full song' },
	{ seconds: 1, label: '1 second' },
	{ seconds: 5, label: '5 seconds' },
	{ seconds: 10, label: '10 seconds' },
	{ seconds: 30, label: '30 seconds' }
];

const SECONDS_KEY = 'swiftster:clip-seconds';
const RANDOM_KEY = 'swiftster:random-start';

function storedSeconds(): number {
	if (!browser) return 0;

	try {
		const value = Number(localStorage.getItem(SECONDS_KEY));
		return CLIPS.some((clip) => clip.seconds === value) ? value : 0;
	} catch {
		// Private mode and blocked site data both throw; the default is fine.
		return 0;
	}
}

function storedRandom(): boolean {
	if (!browser) return false;

	try {
		return localStorage.getItem(RANDOM_KEY) === 'true';
	} catch {
		return false;
	}
}

/**
 * The difficulty settings — how long a clip runs and where it starts — shared
 * between the scanner and the round: each scan is a fresh page load, so a value
 * living in either one would reset every turn.
 */
export const clip = $state({ seconds: storedSeconds(), random: storedRandom() });

export function remember(): void {
	try {
		localStorage.setItem(SECONDS_KEY, String(clip.seconds));
		localStorage.setItem(RANDOM_KEY, String(clip.random));
	} catch {
		// Forgetting the setting is not worth interrupting the game over.
	}
}
