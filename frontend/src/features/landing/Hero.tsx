import { Link } from 'react-router-dom';
import { ArrowRight, Sparkles } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { APP_ENTRY_PATH } from './content';
import { ProductPreview } from './ProductPreview';

export function Hero() {
  return (
    <section aria-labelledby="hero-title" className="relative overflow-hidden pb-16 pt-14 sm:pt-20 lg:pb-24 lg:pt-24">
      <div aria-hidden className="hero-grid pointer-events-none absolute inset-x-0 top-0 h-[520px]" />
      <div
        aria-hidden
        className="pointer-events-none absolute left-1/2 top-0 h-[320px] w-[640px] -translate-x-1/2 rounded-full bg-brand/10 blur-3xl dark:bg-brand/10"
      />

      <div className="container relative">
        <div className="mx-auto max-w-3xl text-center">
          <Badge variant="brand" className="fade-up mb-6 px-3 py-1">
            <Sparkles aria-hidden />
            AI evaluates · Code computes · Faculty decide
          </Badge>

          <h1 id="hero-title" className="fade-up fade-up-delay-1 text-4xl leading-[1.08] tracking-[-0.02em] sm:text-5xl lg:text-[3.75rem]">
            Audit your exam papers, syllabi and grading{' '}
            <span className="text-brand">before</span> they reach students
          </h1>

          <p className="fade-up fade-up-delay-2 mx-auto mt-6 max-w-2xl text-base text-muted-foreground sm:text-lg">
            Faculty Copilot reads the documents you already produce — question papers, marks sheets, rubrics,
            syllabi — and returns evidence-backed findings against your course outcomes. You keep the final call
            on every one.
          </p>

          <div className="fade-up fade-up-delay-3 mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Button asChild size="lg" variant="brand" className="w-full sm:w-auto">
              <Link to={APP_ENTRY_PATH}>
                Get started
                <ArrowRight aria-hidden />
              </Link>
            </Button>
            <Button asChild size="lg" variant="ghost" className="w-full sm:w-auto">
              <a href="#how-it-works">See how it works</a>
            </Button>
          </div>
        </div>

        <div className="fade-up fade-up-delay-3 mt-14 sm:mt-16">
          <ProductPreview />
        </div>
      </div>
    </section>
  );
}
