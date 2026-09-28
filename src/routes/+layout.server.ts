import { appName } from '$lib/server/name';
import type { LayoutServerLoad } from './$types';

// The name is the same on every page on purpose: a title that changed with the
// round would say which round it is.
export const load: LayoutServerLoad = () => ({ name: appName() });
