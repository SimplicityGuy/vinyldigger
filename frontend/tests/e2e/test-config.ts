/**
 * Global test configuration for E2E tests
 */

// Global timeout for test assertions
export const TEST_TIMEOUT = 10000

// CI timeout - longer for slower CI environments
export const CI_TIMEOUT = process.env.CI ? 15000 : TEST_TIMEOUT

// Network timeout for API calls
export const NETWORK_TIMEOUT = 30000
