import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ProgressBar } from '@/components/brain-map/ProgressBar';

describe('<ProgressBar />', () => {
  it('renders percentage when total > 0', () => {
    render(<ProgressBar total={10} passed={3} failed={1} pending={6} />);
    expect(screen.getByText('3/10 (30%)')).toBeInTheDocument();
  });

  it('hides percentage when showLabel is false', () => {
    render(<ProgressBar total={10} passed={3} failed={1} pending={6} showLabel={false} />);
    expect(screen.queryByText('3/10 (30%)')).not.toBeInTheDocument();
  });

  it('handles zero total without division error', () => {
    render(<ProgressBar total={0} passed={0} failed={0} pending={0} />);
    expect(screen.getByText('0/0 (0%)')).toBeInTheDocument();
  });

  it('exposes progress value to assistive tech', () => {
    render(<ProgressBar total={10} passed={5} failed={0} pending={5} />);
    const progress = screen.getByRole('progressbar');
    expect(progress).toHaveAttribute('aria-valuenow', '50');
  });
});
