import { Link } from 'react-router-dom';
import { Logo, PRODUCT_NAME } from '@/components/brand/Logo';
import { APP_ENTRY_PATH, NAV_LINKS } from './content';

export function LandingFooter() {
  return (
    <footer className="border-t border-border bg-muted/40">
      <div className="container flex flex-col gap-8 py-10 md:flex-row md:items-start md:justify-between">
        <div className="max-w-sm">
          <Logo />
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
            Evidence-backed assessment and curriculum review for university faculty. Built for the AUST CSE Carnival
            &lt;8.0/&gt; AI Build Hackathon.
          </p>
        </div>
        <nav aria-label="Footer" className="grid grid-cols-2 gap-x-12 gap-y-2 text-sm sm:grid-cols-3">
          {NAV_LINKS.map((l) => (
            <a key={l.href} href={l.href} className="rounded-sm text-muted-foreground transition-colors duration-fast hover:text-foreground">
              {l.label}
            </a>
          ))}
          <Link to={APP_ENTRY_PATH} className="rounded-sm text-muted-foreground transition-colors duration-fast hover:text-foreground">
            Sign in
          </Link>
        </nav>
      </div>
      <div className="border-t border-border">
        <div className="container flex flex-col gap-2 py-4 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <p>© {new Date().getFullYear()} {PRODUCT_NAME}. Ahsanullah University of Science and Technology.</p>
          <p>AI advises. Faculty decide.</p>
        </div>
      </div>
    </footer>
  );
}
