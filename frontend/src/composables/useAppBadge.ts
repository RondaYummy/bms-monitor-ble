/**
 * SOC number on the installed app's icon (Badging API).
 * iOS 16.4+ (home-screen app), Windows, macOS and ChromeOS show the number; Android Chrome shows a dot.
 */
const STORAGE_KEY = 'badge-soc';

type BadgeNavigator = Navigator & {
  setAppBadge?: (value?: number) => Promise<void>;
  clearAppBadge?: () => Promise<void>;
};

export const isBadgeSupported = () => typeof navigator !== 'undefined' && 'setAppBadge' in navigator;

export function isBadgeEnabled(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === '1';
  } catch {
    return false;
  }
}

export async function setBadgeEnabled(enabled: boolean) {
  try {
    localStorage.setItem(STORAGE_KEY, enabled ? '1' : '0');
  } catch {
    /* private mode */
  }
  if (!enabled) await clearBadge();
}

export async function showSocBadge(soc: number | null | undefined) {
  if (!isBadgeSupported() || !isBadgeEnabled()) return;
  try {
    if (soc === null || soc === undefined || !Number.isFinite(soc)) await clearBadge();
    else await (navigator as BadgeNavigator).setAppBadge?.(Math.max(0, Math.min(100, Math.round(soc))));
  } catch {
    /* ignore */
  }
}

export async function clearBadge() {
  try {
    await (navigator as BadgeNavigator).clearAppBadge?.();
  } catch {
    /* ignore */
  }
}

/** Pack SOC from the per-battery cell info (sum of remaining / sum of nominal capacity). */
export function socFromCellInfo(cellInfo: Record<string, { remaining_capacity?: number; nominal_capacity?: number }>) {
  const batteries = Object.values(cellInfo || {});
  const nominal = batteries.reduce((s, b) => s + (Number(b.nominal_capacity) || 0), 0);
  const remaining = batteries.reduce((s, b) => s + (Number(b.remaining_capacity) || 0), 0);
  return nominal ? (remaining / nominal) * 100 : null;
}
