import { useCallback, useEffect, useState } from 'react';
import { Moon, Sun } from 'lucide-react';
import { Button } from '@/components/ui/button';

const STORAGE_KEY = 'fc-theme';

function readTheme(): 'light' | 'dark' {
  return document.documentElement.classList.contains('dark') ? 'dark' : 'light';
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<'light' | 'dark'>('light');

  useEffect(() => {
    setTheme(readTheme());
  }, []);

  const toggle = useCallback(() => {
    const next = readTheme() === 'dark' ? 'light' : 'dark';
    document.documentElement.classList.toggle('dark', next === 'dark');
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* storage unavailable */
    }
    setTheme(next);
  }, []);

  const label = theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme';

  return (
    <Button variant="ghost" size="icon" onClick={toggle} aria-label={label} title={label}>
      {theme === 'dark' ? <Sun aria-hidden /> : <Moon aria-hidden />}
    </Button>
  );
}
