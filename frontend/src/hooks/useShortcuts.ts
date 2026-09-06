import { useEffect } from 'react';

type Handler = (e: KeyboardEvent) => void;

/**
 * Single-key shortcuts (J/K/A/D…). Ignored while typing in inputs or when modifiers are held,
 * and fully optional: every action must also be reachable by a visible button.
 */
export function useShortcuts(map: Record<string, Handler>, enabled = true) {
  useEffect(() => {
    if (!enabled) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable)) return;
      const h = map[e.key.toLowerCase()];
      if (h) {
        e.preventDefault();
        h(e);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [map, enabled]);
}
