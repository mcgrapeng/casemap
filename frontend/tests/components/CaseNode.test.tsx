import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CaseNode } from '@/components/brain-map/CaseNode';
import type { GraphNode } from '@/lib/types';

const NODE: GraphNode = {
  id: 'c1',
  type: 'positive',
  title: 'User can sign in',
  tags: ['auth'],
  x: 10,
  y: 20,
  width: 160,
  height: 48,
};

describe('<CaseNode />', () => {
  it('renders a focusable group with an accessible name', () => {
    render(<CaseNode node={NODE} status="passed" />);
    const node = screen.getByRole('button', { name: /User can sign in — passed/i });
    expect(node).toHaveAttribute('tabindex', '0');
  });

  it('fires onClick when activated by keyboard', async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(<CaseNode node={NODE} status="pending" onClick={onClick} />);
    const node = screen.getByRole('button', { name: /User can sign in — pending/i });
    node.focus();
    await user.keyboard('{Enter}');
    expect(onClick).toHaveBeenCalledOnce();
  });
});
