import { CircleHelp, Sparkles } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { PROBLEM_POINTS, SOLUTION_POINTS } from './content';
import { Section } from './Section';

export function ProblemSolution() {
  return (
    <Section
      id="problem"
      eyebrow="Why this exists"
      title="Assessment quality is judged by hand, one paper at a time"
      description="Setting a paper, publishing results, calibrating graders — each step raises questions a faculty member answers from memory and intuition. There is rarely time to check."
    >
      <div className="grid gap-6 md:grid-cols-2">
        <Card className="h-full">
          <CardHeader className="p-6 pb-3">
            <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-md bg-muted text-muted-foreground">
              <CircleHelp className="h-5 w-5" aria-hidden />
            </div>
            <CardTitle>The questions that go unanswered</CardTitle>
          </CardHeader>
          <CardContent className="p-6 pt-0">
            <ul className="space-y-3">
              {PROBLEM_POINTS.map((p) => (
                <li key={p} className="flex gap-3 text-sm text-muted-foreground">
                  <span aria-hidden className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-border" />
                  <span>{p}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        <Card className="h-full border-brand/30 bg-gradient-to-b from-brand/[0.06] to-card">
          <CardHeader className="p-6 pb-3">
            <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-md bg-brand text-brand-foreground">
              <Sparkles className="h-5 w-5" aria-hidden />
            </div>
            <CardTitle>What Faculty Copilot does instead</CardTitle>
          </CardHeader>
          <CardContent className="p-6 pt-0">
            <ul className="space-y-3">
              {SOLUTION_POINTS.map((p) => (
                <li key={p} className="flex gap-3 text-sm">
                  <span aria-hidden className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-brand" />
                  <span>{p}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>
    </Section>
  );
}
