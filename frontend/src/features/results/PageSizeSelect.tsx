import { useId } from 'react';
import type { ChangeEvent } from 'react';

interface PageSizeSelectProps {
  readonly pageSize: number;
  readonly pageSizes: readonly number[];
  readonly onChange: (pageSize: number) => void;
}

export default function PageSizeSelect({ pageSize, pageSizes, onChange }: PageSizeSelectProps) {
  const selectId = useId();

  const handleChange = (event: ChangeEvent<HTMLSelectElement>) =>
    onChange(Number(event.target.value));

  return (
    <div className="flex shrink-0 flex-col text-xs text-tertiary">
      <label htmlFor={selectId}>Résultats par page</label>
      <select
        id={selectId}
        value={pageSize}
        onChange={handleChange}
        className="rounded bg-secondary px-2 py-1"
      >
        {pageSizes.map((size) => (
          <option key={size} value={size}>
            {size}
          </option>
        ))}
      </select>
    </div>
  );
}
