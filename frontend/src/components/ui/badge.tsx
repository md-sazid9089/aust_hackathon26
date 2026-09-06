import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/format';

const badgeVariants = cva('inline-flex items-center gap-1 rounded-sm border px-2 py-0.5 text-xs font-semibold transition-colors', {
  variants: {
    variant: {
      default: 'border-transparent bg-primary text-primary-foreground',
      secondary: 'border-transparent bg-muted text-foreground',
      outline: 'text-foreground',
      accent: 'border-transparent bg-accent text-accent-foreground',
      brand: 'border-brand/30 bg-brand/10 text-brand',
      ai: 'border-ai-border/40 bg-ai text-ai-foreground',
      success: 'border-transparent bg-success/15 text-success',
      destructive: 'border-transparent bg-destructive/15 text-destructive',
      info: 'border-transparent bg-sev-info text-sev-info-fg',
      low: 'border-transparent bg-sev-low text-sev-low-fg',
      medium: 'border-transparent bg-sev-medium text-sev-medium-fg',
      high: 'border-transparent bg-sev-high text-sev-high-fg',
    },
  },
  defaultVariants: { variant: 'default' },
});

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
