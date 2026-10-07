import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { StatusControls } from '@/components/brain-map/StatusControls';

describe('<StatusControls />', () => {
  it('renders all status buttons with correct labels', () => {
    render(<StatusControls value="pending" onChange={() => undefined} />);
    expect(screen.getByRole('button', { name: /Mark as 通过/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Mark as 失败/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Mark as 阻塞/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Mark as 跳过/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Mark as 待测/ })).toBeInTheDocument();
  });

  it('marks the current value as pressed', () => {
    render(<StatusControls value="passed" onChange={() => undefined} />);
    const passed = screen.getByRole('button', { name: /Mark as 通过/ });
    expect(passed).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: /Mark as 失败/ })).toHaveAttribute('aria-pressed', 'false');
  });

  it('calls onChange with the clicked status', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<StatusControls value="pending" onChange={onChange} />);
    await user.click(screen.getByRole('button', { name: /Mark as 通过/ }));
    expect(onChange).toHaveBeenCalledWith('passed');
  });

  it('disables all buttons when disabled', () => {
    render(<StatusControls value="pending" onChange={() => undefined} disabled />);
    expect(screen.getAllByRole('button')).toHaveLength(5);
    screen.getAllByRole('button').forEach((b) => expect(b).toBeDisabled());
  });
});
