module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/src'],
  testMatch: ['**/__tests__/**/*.ts', '**/?(*.)+(spec|test).ts'],
  transform: {
    // TS151002 asks for `isolatedModules: true`, which would switch ts-jest to
    // transpile-only and stop type-checking the tests (`tsc` excludes them).
    // The warning targets ESM interop; this package is CommonJS.
    '^.+\\.ts$': ['ts-jest', { diagnostics: { ignoreCodes: [151002] } }],
  },
  collectCoverageFrom: [
    'src/**/*.ts',
    '!src/**/*.d.ts',
    '!src/**/__tests__/**',
    '!src/server.ts',
  ],
  moduleFileExtensions: ['ts', 'js', 'json'],
  verbose: true,
  coverageDirectory: 'coverage',
  coverageReporters: ['text', 'lcov', 'html'],
  
  // Prevent hanging tests
  testTimeout: 10000,
  
  // Clear mocks between tests
  clearMocks: true,
  restoreMocks: true,
  
  // Handle async cleanup
  forceExit: true,
  detectOpenHandles: false,
  
  // Coverage thresholds (optional)
  coverageThreshold: {
    global: {
      branches: 40,
      functions: 60,
      lines: 65,
      statements: 65,
    },
  },
};
