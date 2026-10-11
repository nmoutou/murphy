import type { ReactNode } from 'react';
import { buildPageItems } from './pageItems';

const FIRST_PAGE = 1;

interface PageButtonProps {
  readonly label: string;
  readonly isDisabled: boolean;
  readonly onClick: () => void;
  readonly children: ReactNode;
}

function PageButton({ label, isDisabled, onClick, children }: PageButtonProps) {
  return (
    <button
      type="button"
      aria-label={label}
      disabled={isDisabled}
      onClick={onClick}
      className="rounded px-2 py-1 hover:bg-secondary disabled:opacity-40 disabled:hover:bg-transparent"
    >
      {children}
    </button>
  );
}

interface PaginationProps {
  readonly page: number;
  readonly pageCount: number;
  readonly onGoToPage: (page: number) => void;
}

function PageNumbers({ page, pageCount, onGoToPage }: PaginationProps) {
  return buildPageItems(page, pageCount).map((item) =>
    typeof item === 'string' ? (
      <span key={item} aria-hidden className="px-2">
        …
      </span>
    ) : (
      <button
        key={item}
        type="button"
        aria-label={`Page ${item}`}
        aria-current={item === page ? 'page' : undefined}
        onClick={() => onGoToPage(item)}
        className="rounded px-2 py-1 hover:bg-secondary aria-[current=page]:bg-quaternary aria-[current=page]:text-primary"
      >
        {item}
      </button>
    ),
  );
}

export default function Pagination({ page, pageCount, onGoToPage }: PaginationProps) {
  const isFirst = page === FIRST_PAGE;
  const isLast = page === pageCount;

  return (
    <nav aria-label="Pagination" className="flex items-center justify-center gap-1 py-2 text-sm">
      <PageButton label="Première page" isDisabled={isFirst} onClick={() => onGoToPage(FIRST_PAGE)}>
        «
      </PageButton>
      <PageButton label="Page précédente" isDisabled={isFirst} onClick={() => onGoToPage(page - 1)}>
        ‹ Précédent
      </PageButton>
      <PageNumbers page={page} pageCount={pageCount} onGoToPage={onGoToPage} />
      <PageButton label="Page suivante" isDisabled={isLast} onClick={() => onGoToPage(page + 1)}>
        Suivant ›
      </PageButton>
      <PageButton label="Dernière page" isDisabled={isLast} onClick={() => onGoToPage(pageCount)}>
        »
      </PageButton>
    </nav>
  );
}
