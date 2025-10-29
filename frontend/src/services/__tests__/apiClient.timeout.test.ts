/**
 * Unit tests for ApiClient timeout configuration
 *
 * Testing: P0-1 - Fix UI Display Issue - REST API Timeout Too Short
 * Issue: #541
 *
 * Tests verify that the API client has sufficient timeout for long-running
 * RAG queries (57+ seconds).
 *
 * Note: ApiClient is a singleton, so we test the axios.create configuration.
 */

// Mock axios.create to capture configuration
const mockAxiosInstance = {
  post: jest.fn(),
  get: jest.fn(),
  put: jest.fn(),
  delete: jest.fn(),
  interceptors: {
    request: { use: jest.fn() },
    response: { use: jest.fn() },
  },
};

let capturedConfig: any = null;

jest.mock('axios', () => {
  const mockCreate = jest.fn((config) => {
    capturedConfig = config; // Capture the config
    return mockAxiosInstance;
  });

  return {
    __esModule: true,
    default: {
      create: mockCreate,
    },
    create: mockCreate,
  };
});

describe('ApiClient Timeout Configuration', () => {
  beforeAll(() => {
    // Import ApiClient to trigger singleton creation
    require('../apiClient');
  });

  describe('Default timeout configuration', () => {
    it('should have timeout set to 120 seconds (120000ms) for long-running queries', () => {
      // Assert - Check captured configuration
      expect(capturedConfig).toBeDefined();
      expect(capturedConfig.timeout).toBe(120000); // 120 seconds = 2 minutes
    });

    it('should not have the old 30-second timeout', () => {
      expect(capturedConfig.timeout).not.toBe(30000); // Old timeout
    });

    it('should allow for 20-result queries that take up to 60 seconds with buffer', () => {
      // 120s timeout provides 2x buffer for 60s queries
      expect(capturedConfig.timeout).toBeGreaterThanOrEqual(60000);
      expect(capturedConfig.timeout).toBe(120000);
    });
  });

  describe('Configuration rationale', () => {
    it('should support queries taking longer than the old 30-second timeout', () => {
      // Old timeout was 30 seconds, new should be significantly higher
      expect(capturedConfig.timeout).toBeGreaterThan(30000);
    });

    it('should provide reasonable upper bound (not infinite)', () => {
      // Should timeout eventually (not infinite)
      expect(capturedConfig.timeout).toBeLessThan(300000); // Less than 5 minutes
    });
  });
});
