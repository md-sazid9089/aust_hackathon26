import { Features } from './Features';
import { FinalCta } from './FinalCta';
import { Hero } from './Hero';
import { HowItWorks } from './HowItWorks';
import { LandingFooter } from './LandingFooter';
import { LandingNav } from './LandingNav';
import { Principles } from './Principles';
import { ProblemSolution } from './ProblemSolution';

export default function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col overflow-x-hidden bg-background text-foreground">
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <LandingNav />
      <main id="main" className="flex-1">
        <Hero />
        <ProblemSolution />
        <Features />
        <HowItWorks />
        <Principles />
        <FinalCta />
      </main>
      <LandingFooter />
    </div>
  );
}
