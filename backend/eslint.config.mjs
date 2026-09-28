import js from '@eslint/js';
import { defineConfig } from 'eslint/config';
import tseslint from 'typescript-eslint';

// The size and shape limits of CLAUDE.md, checked instead of remembered
const MAX_FILE_LINES = 300;
const MAX_FUNCTION_LINES = 30;
const MAX_DEPTH = 3;
const MAX_PARAMS = 4;
const MAX_COMPLEXITY = 10;

export default defineConfig(
  {
    files: ['src/**/*.ts'],
    extends: [js.configs.recommended, tseslint.configs.recommended],
    rules: {
      // Express reads a handler's arity: `_next` must stay declared even when unused.
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', caughtErrorsIgnorePattern: '^_' },
      ],
      'max-lines': ['error', { max: MAX_FILE_LINES }],
      'max-lines-per-function': [
        'error',
        { max: MAX_FUNCTION_LINES, skipBlankLines: true, skipComments: true },
      ],
      'max-depth': ['error', MAX_DEPTH],
      'max-params': ['error', MAX_PARAMS],
      complexity: ['error', MAX_COMPLEXITY],
      'no-magic-numbers': [
        'error',
        { ignore: [0, 1, -1], ignoreArrayIndexes: true, ignoreDefaultValues: true },
      ],
    },
  },
  {
    // A `describe` block is a list of cases, and expected values read best in place
    files: ['src/__tests__/**/*.ts', 'src/**/*.test.ts'],
    rules: {
      'max-lines-per-function': 'off',
      'no-magic-numbers': 'off',
    },
  },
);
