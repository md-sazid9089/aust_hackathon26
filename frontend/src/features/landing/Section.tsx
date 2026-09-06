import type { HTMLAttributes, ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { useReveal } from './useReveal';

interface SectionProps extends HTMLAttributes<HTMLElement> {
  id?: string;
  eyebrow?: string;
  title?: string;
  description?: string;
  children: ReactNode;
  contentClassName?: string;
}

/** Landing section with consistent width, vertical rhythm and one-shot reveal. */
export function Section({ id, eyebrow, title, description, children, className, contentClassName, ...rest }: SectionProps) {
  const { ref, visible } = useReveal<HTMLElement>();
  const headingId = id ? `${id}-title` : undefined;

  return (
    <section
      id={id}
      ref={ref}
      aria-labelledby={headingId}
      className={cn('py-16 sm:py-20 lg:py-24', className)}
      data-visible={visible}
      {...rest}
    >
      <div className="container">
        {(eyebrow || title || description) && (
          <div className={cn('mx-auto max-w-2xl text-center reveal', visible && 'is-visible')}>
            {eyebrow && (
              <p className="mb-3 text-xs font-semibold uppercase tracking-[0.14em] text-brand">{eyebrow}</p>
            )}
            {title && (
              <h2 id={headingId} className="text-3xl sm:text-4xl">
                {title}
              </h2>
            )}
            {description && <p className="mt-4 text-base text-muted-foreground sm:text-lg">{description}</p>}
          </div>
        )}
        <div className={cn('mt-12 reveal reveal-delay-1', visible && 'is-visible', contentClassName)}>{children}</div>
      </div>
    </section>
  );
}
