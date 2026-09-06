import { STEPS } from './content';
import { Section } from './Section';

export function HowItWorks() {
  return (
    <Section
      id="how-it-works"
      eyebrow="How it works"
      title="From upload to accepted findings in four steps"
      description="A single journey: you give the system something, it inspects it, and you receive something you can act on."
    >
      <ol className="relative grid gap-8 lg:grid-cols-4 lg:gap-6">
        <div
          aria-hidden
          className="absolute left-5 top-0 h-full w-px bg-border lg:left-0 lg:top-5 lg:h-px lg:w-full"
        />
        {STEPS.map((s) => (
          <li key={s.number} className="relative flex gap-5 lg:flex-col lg:gap-4">
            <div className="relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-border bg-card text-brand shadow-sm">
              <s.icon className="h-[18px] w-[18px]" strokeWidth={1.75} aria-hidden />
            </div>
            <div className="pt-1 lg:pt-0">
              <p className="tabular text-xs font-semibold uppercase tracking-[0.14em] text-brand">Step {s.number}</p>
              <h3 className="mt-1 text-lg">{s.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{s.description}</p>
            </div>
          </li>
        ))}
      </ol>
    </Section>
  );
}
