import { env } from '$env/dynamic/private';

/**
 * What this server calls itself, in the tab and at the top of the page. Read
 * per request rather than baked in, so the published image can be named by
 * whoever runs it.
 */
export function appName(): string {
	return env.APP_NAME?.trim() || 'swiftster';
}
