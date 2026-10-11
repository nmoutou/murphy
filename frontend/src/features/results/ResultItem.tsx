import type { SearchResult } from '@murphy/contract/search';
import DocumentIcon from './DocumentIcon';
import InForceDot from './InForceDot';

interface ResultItemProps {
  readonly result: SearchResult;
  readonly onOpenDocument: (result: SearchResult) => void;
}

/** Le menu n'a pas encore d'option */
function ResultMenu({ title }: { readonly title: string }) {
  return (
    <button
      type="button"
      aria-label={`Options de ${title}`}
      disabled
      className="shrink-0 px-1 disabled:opacity-60"
    >
      …
    </button>
  );
}

export default function ResultItem({ result, onOpenDocument }: ResultItemProps) {
  const { title, documentType, nature, isInForce, passages } = result;
  // Le mieux classé
  const passage = passages[0];

  return (
    <li className="flex items-center gap-3 border-b border-secondary py-3">
      <ResultMenu title={title} />
      <article className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <InForceDot isInForce={isInForce} />
          <DocumentIcon documentType={documentType} nature={nature} />
          <button
            type="button"
            onClick={() => onOpenDocument(result)}
            className="text-left font-mono text-quaternary hover:underline"
          >
            {title}
          </button>
        </div>
        {passage && <p className="mt-1 line-clamp-3 text-sm">{passage.text}</p>}
      </article>
    </li>
  );
}
