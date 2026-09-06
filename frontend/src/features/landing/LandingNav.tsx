import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Menu, X } from 'lucide-react';
import { Logo } from '@/components/brand/Logo';
import { ThemeToggle } from '@/components/theme/ThemeToggle';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { APP_ENTRY_PATH, NAV_LINKS } from './content';

export function LandingNav() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <header
      className={cn(
        'sticky top-0 z-50 border-b transition-colors duration-fast',
        scrolled || open
          ? 'border-border bg-background/90 backdrop-blur supports-[backdrop-filter]:bg-background/75'
          : 'border-transparent bg-transparent',
      )}
    >
      <div className="container flex h-16 items-center justify-between">
        <Link to="/" aria-label="Faculty Copilot — home" className="rounded-md">
          <Logo />
        </Link>

        <nav aria-label="Primary" className="hidden items-center gap-1 md:flex">
          {NAV_LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="rounded-md px-3 py-2 text-sm text-muted-foreground transition-colors duration-fast hover:bg-muted hover:text-foreground"
            >
              {l.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Button asChild variant="brand" className="hidden sm:inline-flex">
            <Link to={APP_ENTRY_PATH}>
              Get started
              <ArrowRight aria-hidden />
            </Link>
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            aria-expanded={open}
            aria-controls="landing-mobile-nav"
            aria-label={open ? 'Close menu' : 'Open menu'}
            onClick={() => setOpen((v) => !v)}
          >
            {open ? <X aria-hidden /> : <Menu aria-hidden />}
          </Button>
        </div>
      </div>

      {open && (
        <nav
          id="landing-mobile-nav"
          aria-label="Primary mobile"
          className="container flex flex-col gap-1 border-t border-border pb-4 pt-2 md:hidden animate-in fade-in slide-in-from-top-1 duration-fast"
        >
          {NAV_LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              onClick={() => setOpen(false)}
              className="rounded-md px-3 py-2.5 text-sm text-foreground transition-colors duration-fast hover:bg-muted"
            >
              {l.label}
            </a>
          ))}
          <Button asChild variant="brand" className="mt-2 w-full">
            <Link to={APP_ENTRY_PATH}>
              Get started
              <ArrowRight aria-hidden />
            </Link>
          </Button>
        </nav>
      )}
    </header>
  );
}
