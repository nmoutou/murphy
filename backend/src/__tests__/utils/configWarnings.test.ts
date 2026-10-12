import { checkEnvironment } from '../../utils/configWarnings';

jest.mock('../../utils/logger', () => ({ logger: { info: jest.fn(), warn: jest.fn(), error: jest.fn() } }));

describe('checkEnvironment', () => {
  it('stops the boot, naming every missing required variable', () => {
    const report = { missingRequired: ['LLM_API_KEY', 'LLM_MODEL'], defaulted: [] };

    expect(() => checkEnvironment(report)).toThrow('Critical env vars missing: LLM_API_KEY, LLM_MODEL');
  });

  it('lets the boot go on when only optional variables fall back on their defaults', () => {
    expect(() => checkEnvironment({ missingRequired: [], defaulted: ['LLM_TIMEOUT'] })).not.toThrow();
  });
});
