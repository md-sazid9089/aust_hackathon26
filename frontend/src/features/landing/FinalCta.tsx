import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { APP_ENTRY_PATH } from './content';
import { useReveal } from './useReveal';

export function FinalCta() {
  const { ref, visible } = useReveal<HTMLElement>();
  return (
    <section ref={ref} aria-labelledby="cta-title" className="py-16 sm:py-20 lg:py-24">
      <div className="container">
        <div
          className={cn(
            'reveal relative overflow-hidden rounded-lg border border-border bg-card px-6 py-14 text-center shadow-sm sm:px-12',
            visible && 'is-visible',
          )}
        >
          <div
            aria-hidden
            className="pointer-events-none absolute -right-24 -top-24 h-64 w-64 rounded-full bg-brand/15 blur-3xl"
          />
          <div className="relative mx-auto max-w-2xl">
            <h2 id="cta-title" className="text-3xl sm:text-4xl">
              Ready to audit your next paper?
            </h2>
            <p className="mt-4 text-base text-muted-foreground sm:text-lg">
              Sign in, load the demo course, and see the full journey — upload, findings, decision, export — in a few
              minutes.
            </p>
            <div className="mt-8 flex justify-center">
              <Button asChild size="lg" variant="brand" className="w-full sm:w-auto">
                <Link to={APP_ENTRY_PATH}>
                  Get started
                  <ArrowRight aria-hidden />
                </Link>
              </Button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
