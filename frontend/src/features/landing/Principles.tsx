import { PRINCIPLES } from './content';
import { Section } from './Section';

export function Principles() {
  return (
    <Section
      id="principles"
      eyebrow="Designed to be trusted"
      title="A tool that advises, not one that decides"
      description="The brief is simple: AI should help faculty understand, compare and evaluate — not replace their judgement."
      className="bg-muted/40"
    >
      <ul className="grid gap-6 md:grid-cols-3">
        {PRINCIPLES.map((p) => (
          <li key={p.title} className="rounded-lg border border-border bg-card p-6 shadow-sm">
            <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-md bg-brand/10 text-brand">
              <p.icon className="h-5 w-5" strokeWidth={1.75} aria-hidden />
            </div>
            <h3 className="text-lg">{p.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{p.description}</p>
          </li>
        ))}
      </ul>
    </Section>
  );
}
