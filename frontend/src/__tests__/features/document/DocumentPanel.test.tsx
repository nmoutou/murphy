import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import type { DocumentContent, Passage } from '@murphy/contract/search';
import DocumentPanel from '@/features/document/DocumentPanel';
import { ApiError } from '@/lib/api/apiError';
import { fetchDocument } from '@/lib/api/documents';

vi.mock('@/lib/api/documents', () => ({ fetchDocument: vi.fn() }));

const IDENTIFIER = 'LEGIARTI000049431213';
const DOCUMENT: DocumentContent = {
  identifier: IDENTIFIER,
  title: 'Article 2224',
  content: 'Les actions personnelles se prescrivent par cinq ans.',
};
const PASSAGE: Passage = { chunkId: 'chunk-1', text: 'se prescrivent', start: 25, end: 39 };

const fetchMock = vi.mocked(fetchDocument);

beforeEach(() => {
  fetchMock.mockReset();
  fetchMock.mockResolvedValue(DOCUMENT);
});

describe('DocumentPanel', () => {
  it('says the document is loading', () => {
    fetchMock.mockReturnValue(new Promise(() => {}));

    render(<DocumentPanel identifier={IDENTIFIER} onError={vi.fn()} />);

    expect(screen.getByRole('status')).toHaveTextContent('Chargement du document…');
  });

  it('shows the full text, the passage highlighted and scrolled into view', async () => {
    const scrollIntoView = vi.spyOn(Element.prototype, 'scrollIntoView');

    render(<DocumentPanel identifier={IDENTIFIER} passage={PASSAGE} onError={vi.fn()} />);

    const mark = await screen.findByText('se prescrivent');
    expect(mark.tagName).toBe('MARK');
    expect(mark.parentElement).toHaveTextContent(DOCUMENT.content);
    expect(screen.getByRole('heading', { name: 'Article 2224' })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(IDENTIFIER, expect.any(AbortSignal));
    expect(scrollIntoView.mock.contexts).toEqual([mark]);
  });

  it('highlights nothing without a passage', async () => {
    const { container } = render(<DocumentPanel identifier={IDENTIFIER} onError={vi.fn()} />);

    expect(await screen.findByText(DOCUMENT.content)).toBeInTheDocument();
    expect(container.querySelector('mark')).toBeNull();
  });

  it('hands the error code to onError', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    fetchMock.mockRejectedValue(new ApiError('DOCUMENT_NOT_FOUND', 'HTTP 404'));
    const onError = vi.fn();

    render(<DocumentPanel identifier={IDENTIFIER} onError={onError} />);

    await vi.waitFor(() => expect(onError).toHaveBeenCalledExactlyOnceWith('DOCUMENT_NOT_FOUND'));
  });

  it('aborts the request when closed before the answer', () => {
    fetchMock.mockReturnValue(new Promise(() => {}));
    const { unmount } = render(<DocumentPanel identifier={IDENTIFIER} onError={vi.fn()} />);

    unmount();

    expect(fetchMock.mock.lastCall?.[1].aborted).toBe(true);
  });
});
