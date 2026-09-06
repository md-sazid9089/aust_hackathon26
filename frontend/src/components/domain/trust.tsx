import type { ReactNode } from 'react';
import { Calculator, Sparkles } from 'lucide-react';
import { cn } from '@/lib/format';

/** Visual contract: deterministic numbers vs LLM prose (MASTER.md rationale row 4). */
export function ComputedLabel({ className }: { className?: string }) {
  return (
    <span className={cn('inline-flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-measure', className)}>
      <Calculator className="h-3.5 w-3.5" aria-hidden /> Computed
    </span>
  );
}

export function AiLabel({ className }: { className?: string }) {
  return (
    <span className={cn('inline-flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-ai-foreground', className)}>
      <Sparkles className="h-3.5 w-3.5" aria-hidden /> AI explanation
    </span>
  );
}

export function AiBlock({ children, className, label = true }: { children: ReactNode; className?: string; label?: boolean }) {
  return (
    <div className={cn('rounded-md border border-ai-border bg-ai-surface p-3 text-base text-foreground', className)}>
      {label && <AiLabel className="mb-1.5" />}
      <div className="leading-relaxed">{children}</div>
    </div>
  );
}

export function Stat({ label, value, hint, computed = true, className }: { label: string; value: ReactNode; hint?: ReactNode; computed?: boolean; className?: string }) {
  return (
    <div className={cn('rounded-lg border bg-card p-4', className)}>
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="mt-1 text-3xl font-semibold tabular text-foreground">{value}</p>
      <div className="mt-1 flex items-center justify-between gap-2 text-xs text-muted-foreground">
        <span>{hint}</span>
        {computed && <ComputedLabel />}
      </div>
    </div>
  );
}

export function Evidence({ children, lang }: { children: ReactNode; lang?: string }) {
  return (
    <blockquote lang={lang} className="border-l-2 border-border bg-muted/50 px-3 py-2 text-sm text-foreground">
      {children}
    </blockquote>
  );
}
