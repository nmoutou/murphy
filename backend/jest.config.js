module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/src'],
  testMatch: ['**/__tests__/**/*.ts', '**/?(*.)+(spec|test).ts'],
  transform: {
    // TS151002 réclame `isolatedModules: true`, qui passerait ts-jest en transpilation
    // seule : les tests ne seraient plus typés (`tsc` les exclut). L'avertissement vise
    // l'interop ESM ; ce paquet est CommonJS.
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
  
  testTimeout: 10000,
  
  clearMocks: true,
  restoreMocks: true,

  // Vérifié seulement par `jest --coverage`
  coverageThreshold: {
    global: {
      branches: 40,
      functions: 60,
      lines: 65,
      statements: 65,
    },
  },
};
