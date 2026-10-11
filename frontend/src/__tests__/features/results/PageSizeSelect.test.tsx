import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PageSizeSelect from '@/features/results/PageSizeSelect';

describe('PageSizeSelect', () => {
  it('offers the sizes of the response, the current one selected', () => {
    render(<PageSizeSelect pageSize={25} pageSizes={[10, 25, 50]} onChange={vi.fn()} />);

    const select = screen.getByRole('combobox', { name: 'Résultats par page' });
    expect(select).toHaveValue('25');
    expect(screen.getAllByRole('option').map((option) => option.textContent)).toEqual([
      '10',
      '25',
      '50',
    ]);
  });

  it('passes the chosen size as a number', async () => {
    const onChange = vi.fn();
    render(<PageSizeSelect pageSize={10} pageSizes={[10, 25, 50]} onChange={onChange} />);

    await userEvent.selectOptions(screen.getByRole('combobox'), '50');

    expect(onChange).toHaveBeenCalledExactlyOnceWith(50);
  });
});
