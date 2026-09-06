import { describe, expect, it, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { FindingCard } from '@/components/domain/FindingList';
import type { Finding } from '@/lib/types/api';

const finding: Finding = {
  id: 'f1',
  run_id: 'r1',
  type: 'coverage_gap',
  severity: 'high',
  title: 'CO4 is not assessed',
  rationale: 'No question maps to CO4.',
  evidence_snippet: 'Q1–Q8 map to CO1, CO2, CO3 only.',
  target_kind: 'course_outcome',
  target_id: 'co-4',
  target_label: 'CO4',
  payload: { marks: 0 },
  status: 'open',
  decided_at: null,
};

describe('FindingCard', () => {
  it('separates computed numbers from AI rationale and exposes decisions', () => {
    const onDecide = vi.fn();
    render(<FindingCard finding={finding} onDecide={onDecide} />);
    expect(screen.getByRole('heading', { name: 'CO4 is not assessed' })).toBeInTheDocument();
    expect(screen.getByText('Computed')).toBeInTheDocument();
    expect(screen.getByText('AI explanation')).toBeInTheDocument();
    expect(screen.getByText('No question maps to CO4.')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /accept/i }));
    expect(onDecide).toHaveBeenCalledWith('accepted');
  });

  it('hides decision controls when read-only', () => {
    render(<FindingCard finding={finding} readOnly onDecide={() => {}} />);
    expect(screen.queryByRole('button', { name: /accept/i })).not.toBeInTheDocument();
  });
});
