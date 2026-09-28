import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

// The size and shape limits of CLAUDE.md, checked instead of remembered
const MAX_FILE_LINES = 300;
const MAX_COMPONENT_FILE_LINES = 200;
const MAX_FUNCTION_LINES = 30;
const MAX_DEPTH = 3;
const MAX_PARAMS = 4;
const MAX_COMPLEXITY = 10;

export default defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    files: ["src/**/*.{ts,tsx}"],
    rules: {
      "max-lines": ["error", { max: MAX_FILE_LINES }],
      "max-lines-per-function": [
        "error",
        { max: MAX_FUNCTION_LINES, skipBlankLines: true, skipComments: true },
      ],
      "max-depth": ["error", MAX_DEPTH],
      "max-params": ["error", MAX_PARAMS],
      complexity: ["error", MAX_COMPLEXITY],
      "no-magic-numbers": [
        "error",
        { ignore: [0, 1, -1], ignoreArrayIndexes: true, ignoreDefaultValues: true },
      ],
    },
  },
  {
    files: ["src/**/*.tsx"],
    rules: {
      "max-lines": ["error", { max: MAX_COMPONENT_FILE_LINES }],
    },
  },
  {
    // A `describe` block is a list of cases, and expected values read best in place
    files: ["src/**/*.test.{ts,tsx}"],
    rules: {
      "max-lines-per-function": "off",
      "no-magic-numbers": "off",
    },
  },
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts"]),
]);
