module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/src'],
  testMatch: ['**/__tests__/**/*.ts', '**/?(*.)+(spec|test).ts'],
  transform: {
    '^.+\\.ts$': 'ts-jest',
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
