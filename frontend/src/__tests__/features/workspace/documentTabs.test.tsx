import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DockviewReact } from 'dockview-react';
import type { DockviewApi, DockviewReadyEvent } from 'dockview-react';
import type { SearchResult } from '@murphy/contract/search';
import { applyDefaultLayout } from '@/features/workspace/defaultLayout';
import { openDocument } from '@/features/workspace/documentTabs';
import { PANEL_COMPONENTS } from '@/features/workspace/panelRegistry';
import PanelTab from '@/features/workspace/PanelTab';
import Workspace from '@/features/workspace/Workspace';
import { ApiError } from '@/lib/api/apiError';
import { fetchDocument } from '@/lib/api/documents';
import { useErrorStore } from '@/stores/errorStore';
import { useSearchStore } from '@/stores/searchStore';

vi.mock('@/lib/api/documents', () => ({ fetchDocument: vi.fn() }));

const CONTENT = 'Les actions personnelles se prescrivent par cinq ans.';
const RESULT: SearchResult = {
  identifier: 'LEGIARTI000049431213',
  title: 'Article 2224',
  documentType: 'article',
  contentLength: 53,
  passages: [{ chunkId: 'chunk-1', text: 'se prescrivent', start: 25, end: 39 }],
};
const DOCUMENT_PANEL_ID = `document:${RESULT.identifier}`;

const fetchMock = vi.mocked(fetchDocument);

/** L'espace par défaut, son API à portée du test */
const renderDockview = (): DockviewApi => {
  let readyApi: DockviewApi | undefined;
  render(
    <DockviewReact
      components={PANEL_COMPONENTS}
      defaultTabComponent={PanelTab}
      onReady={({ api }: DockviewReadyEvent) => {
        applyDefaultLayout(api);
        readyApi = api;
      }}
    />,
  );
  if (!readyApi) throw new Error('Dockview was not ready after the first render');
  return readyApi;
};

beforeEach(() => {
  fetchMock.mockReset();
  fetchMock.mockResolvedValue({
    identifier: RESULT.identifier,
    title: RESULT.title,
    content: CONTENT,
    contentLength: CONTENT.length,
  });
  useErrorStore.setState(useErrorStore.getInitialState(), true);
  useSearchStore.setState({
    status: 'success',
    response: {
      page: 1,
      pageCount: 1,
      pageSize: 10,
      pageSizes: [10],
      contextBudget: 100_000,
      results: [RESULT],
    },
  });
});

describe('document tabs', () => {
  it('opens a result in a tab next to Recherche, its passage highlighted', async () => {
    const { container } = render(<Workspace />);

    await userEvent.click(await screen.findByRole('button', { name: RESULT.title }));

    expect(await screen.findByText('se prescrivent', { selector: 'mark' })).toBeInTheDocument();
    expect(container.querySelectorAll('.dv-groupview')).toHaveLength(1);
  });

  it('activates the tab of a document already open instead of opening another', () => {
    const api = renderDockview();
    act(() => openDocument(api, RESULT));
    act(() => api.getPanel('results')?.api.setActive());

    act(() => openDocument(api, RESULT));

    expect(api.panels.filter((panel) => panel.id === DOCUMENT_PANEL_ID)).toHaveLength(1);
    expect(api.activePanel?.id).toBe(DOCUMENT_PANEL_ID);
  });

  it('opens in the active group once Recherche is closed', () => {
    const api = renderDockview();
    const graph = api.getPanel('graph');
    act(() => {
      api.getPanel('results')?.api.close();
      graph?.api.moveTo({ group: api.addGroup({ direction: 'right' }) });
      graph?.api.setActive();
    });

    act(() => openDocument(api, RESULT));

    expect(api.getPanel(DOCUMENT_PANEL_ID)?.group).toBe(graph?.group);
  });

  it('closes the tab of an unreadable document and shows the error', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    fetchMock.mockRejectedValue(new ApiError('DOCUMENT_NOT_FOUND', 'HTTP 404'));
    const api = renderDockview();

    act(() => openDocument(api, RESULT));

    await vi.waitFor(() => expect(api.getPanel(DOCUMENT_PANEL_ID)).toBeUndefined());
    expect(useErrorStore.getState().errorCode).toBe('DOCUMENT_NOT_FOUND');
  });
});
