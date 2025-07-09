import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : 'html',

  // Global setup to ensure backend is running
  globalSetup: './playwright.global-setup.ts',
  globalTeardown: './playwright.global-teardown.ts',

  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    headless: true, // Always use headless mode
    actionTimeout: 10000,
    navigationTimeout: 30000,
  },

  projects: [
    // Desktop browsers
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },

    // Mobile browsers
    {
      name: 'mobile-safari-iphone',
      use: { ...devices['iPhone 14'] },
    },
    {
      name: 'mobile-safari-ipad',
      use: { ...devices['iPad Pro 11'] },
    },
  ],

  // Disable webServer since we're using Docker Compose
  // webServer: {
  //   command: 'npm run dev',
  //   port: 3000,
  //   reuseExistingServer: !process.env.CI,
  //   timeout: 120000,
  // },

  // Global timeout
  timeout: process.env.CI ? 60000 : 30000,

  // Expect timeout
  expect: {
    timeout: 5000,
  },
})
