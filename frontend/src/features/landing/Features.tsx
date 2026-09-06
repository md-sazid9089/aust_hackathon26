import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { FEATURES } from './content';
import { Section } from './Section';

export function Features() {
  return (
    <Section
      id="features"
      eyebrow="Four modules, one workspace"
      title="Built around the documents you already produce"
      description="Each module takes one artefact and returns findings against the same course outcomes — so nothing is entered twice."
      className="bg-muted/40"
    >
      <ul className="grid gap-5 sm:grid-cols-2">
        {FEATURES.map((f) => (
          <li key={f.title}>
            <Card className="group h-full transition-all duration-fast hover:-translate-y-0.5 hover:shadow-md">
              <CardHeader className="p-6 pb-2">
                <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-md border border-border bg-background text-brand transition-colors duration-fast group-hover:border-brand/40 group-hover:bg-brand/5">
                  <f.icon className="h-5 w-5" strokeWidth={1.75} aria-hidden />
                </div>
                <CardTitle className="text-lg">{f.title}</CardTitle>
              </CardHeader>
              <CardContent className="p-6 pt-0">
                <CardDescription className="leading-relaxed">{f.description}</CardDescription>
              </CardContent>
            </Card>
          </li>
        ))}
      </ul>
    </Section>
  );
}
