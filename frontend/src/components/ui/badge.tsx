import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors duration-fast [&_svg]:size-3.5',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-primary text-primary-foreground',
        secondary: 'border-transparent bg-muted text-foreground',
        outline: 'border-border bg-card text-muted-foreground',
        ai: 'border-ai-border/40 bg-ai text-ai-foreground',
        brand: 'border-brand/30 bg-brand/10 text-brand',
        measure: 'border-transparent bg-sev-low text-sev-low-fg',
        info: 'border-transparent bg-sev-info text-sev-info-fg',
        medium: 'border-transparent bg-sev-medium text-sev-medium-fg',
        high: 'border-transparent bg-sev-high text-sev-high-fg',
      },
    },
    defaultVariants: { variant: 'default' },
  },
);

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
