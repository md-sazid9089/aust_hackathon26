import { ShieldCheck } from 'lucide-react';
import { cn } from '@/lib/utils';

export const PRODUCT_NAME = 'Faculty Copilot';

interface LogoProps {
  className?: string;
  showText?: boolean;
}

export function Logo({ className, showText = true }: LogoProps) {
  return (
    <span className={cn('inline-flex items-center gap-2.5', className)}>
      <span className="flex h-8 w-8 items-center justify-center rounded-md bg-brand text-brand-foreground">
        <ShieldCheck className="h-[18px] w-[18px]" strokeWidth={1.75} aria-hidden />
      </span>
      {showText && (
        <span className="font-heading text-lg font-semibold leading-none tracking-tight text-foreground">
          {PRODUCT_NAME}
        </span>
      )}
    </span>
  );
}
