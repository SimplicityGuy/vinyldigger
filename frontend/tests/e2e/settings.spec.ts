import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'

// Helper to set up authenticated state
async function setupAuthentication(page: Page) {
  await page.addInitScript(() => {
    window.sessionStorage.setItem('access_token', 'mock-access-token')
    window.localStorage.setItem('refresh_token', JSON.stringify({
      token: 'mock-refresh-token',
      expiry: Date.now() + 86400000,
    }))
  })

  // Mock user API response
  await page.route('/api/v1/auth/me', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: '123',
        email: 'test@example.com',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }),
    })
  })
}

test.describe('Settings Page', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthentication(page)

    // Mock API keys response
    await page.route('/api/v1/config/api-keys', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            service: 'discogs',
            has_key: true,
            created_at: new Date(Date.now() - 604800000).toISOString(),
            updated_at: new Date(Date.now() - 604800000).toISOString(),
          },
          {
            service: 'ebay',
            has_key: false,
          },
        ]),
      })
    })

    // Mock preferences response
    await page.route('/api/v1/config/preferences', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          email_notifications: true,
          notification_frequency: 'daily',
          currency: 'USD',
          default_search_platform: 'both',
          min_record_condition: 'VG+',
          min_sleeve_condition: 'VG',
          seller_location_preference: 'US',
          check_interval_hours: 24,
        }),
      })
    })
  })

  test('should display all settings sections', async ({ page }) => {
    await page.goto('/settings')

    // Check page header
    await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible()
    await expect(page.getByText('Manage your account and application settings')).toBeVisible()

    // Check API Keys section
    await expect(page.getByText('API Keys')).toBeVisible()
    await expect(page.getByText('Connect your Discogs and eBay accounts')).toBeVisible()

    // Check Discogs configuration
    await expect(page.getByText('Discogs API')).toBeVisible()
    await expect(page.getByText('Configured')).toBeVisible()
    await expect(page.getByText('••••••••')).toBeVisible() // Masked API key

    // Check eBay configuration
    await expect(page.getByText('eBay API')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Configure eBay API' })).toBeVisible()

    // Check Preferences section
    await expect(page.getByText('Preferences')).toBeVisible()
    await expect(page.getByText('Customize your VinylDigger experience')).toBeVisible()
  })

  test('should configure Discogs API key', async ({ page }) => {
    // Mock update API key endpoint
    await page.route('/api/v1/config/api-keys', async (route) => {
      if (route.request().method() === 'PUT') {
        const body = await route.request().postDataJSON()
        expect(body).toEqual({
          service: 'discogs',
          key: 'test-discogs-token',
          secret: 'test-discogs-secret',
        })

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            service: 'discogs',
            has_key: true,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          }),
        })
      } else {
        // GET request
        await route.continue()
      }
    })

    await page.goto('/settings')

    // Click configure button for Discogs
    await page.getByRole('button', { name: 'Configure Discogs API' }).click()

    // Fill in API credentials
    await page.getByLabel('API Token').fill('test-discogs-token')
    await page.getByLabel('API Secret').fill('test-discogs-secret')

    // Save configuration
    await page.getByRole('button', { name: /save.*discogs/i }).click()

    // Should show success toast
    await expect(page.getByText('API key updated')).toBeVisible()
    await expect(page.getByText('Your Discogs API key has been saved.')).toBeVisible()
  })

  test('should configure eBay API credentials', async ({ page }) => {
    // Mock update API key endpoint
    await page.route('/api/v1/config/api-keys', async (route) => {
      if (route.request().method() === 'PUT') {
        const body = await route.request().postDataJSON()
        expect(body).toEqual({
          service: 'ebay',
          key: 'test-ebay-client-id',
          secret: 'test-ebay-client-secret',
        })

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            service: 'ebay',
            has_key: true,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          }),
        })
      } else {
        await route.continue()
      }
    })

    await page.goto('/settings')

    // Click configure button for eBay
    await page.getByRole('button', { name: 'Configure eBay API' }).click()

    // Fill in API credentials
    await page.getByLabel('Client ID').fill('test-ebay-client-id')
    await page.getByLabel('Client Secret').fill('test-ebay-client-secret')

    // Save configuration
    await page.getByRole('button', { name: /save.*ebay/i }).click()

    // Should show success toast
    await expect(page.getByText('API key updated')).toBeVisible()
    await expect(page.getByText('Your eBay API key has been saved.')).toBeVisible()
  })

  test('should display current preferences', async ({ page }) => {
    await page.goto('/settings')

    // Check email notifications
    await expect(page.getByText('Email Notifications')).toBeVisible()
    await expect(page.getByText('Enabled')).toBeVisible()

    // Check notification frequency
    await expect(page.getByText('Notification Frequency')).toBeVisible()
    await expect(page.getByText('daily')).toBeVisible()

    // Check currency
    await expect(page.getByText('Currency')).toBeVisible()
    await expect(page.getByText('USD')).toBeVisible()

    // Check default platform
    await expect(page.getByText('Default Search Platform')).toBeVisible()
    await expect(page.getByText('both')).toBeVisible()

    // Check additional preferences
    await expect(page.getByText('Minimum Record Condition')).toBeVisible()
    await expect(page.getByText('VG+')).toBeVisible()

    await expect(page.getByText('Minimum Sleeve Condition')).toBeVisible()
    await expect(page.getByText('VG', { exact: true })).toBeVisible()

    await expect(page.getByText('Seller Location')).toBeVisible()
    await expect(page.getByText('US')).toBeVisible()

    await expect(page.getByText('Check Interval')).toBeVisible()
    await expect(page.getByText('Every 24 hours')).toBeVisible()
  })

  test('should handle API key configuration errors', async ({ page }) => {
    // Mock error response
    await page.route('/api/v1/config/api-keys', async (route) => {
      if (route.request().method() === 'PUT') {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({
            detail: 'Invalid API credentials',
          }),
        })
      } else {
        await route.continue()
      }
    })

    await page.goto('/settings')

    // Try to configure Discogs
    await page.getByRole('button', { name: 'Configure Discogs API' }).click()
    await page.getByLabel('API Token').fill('invalid-token')
    await page.getByLabel('API Secret').fill('invalid-secret')
    await page.getByRole('button', { name: /save.*discogs/i }).click()

    // Should show error toast
    await expect(page.getByText('Failed to update API key')).toBeVisible()
    await expect(page.getByText('Invalid API credentials')).toBeVisible()
  })

  test('should clear form when canceling configuration', async ({ page }) => {
    await page.goto('/settings')

    // Open Discogs configuration
    await page.getByRole('button', { name: 'Configure Discogs API' }).click()

    // Fill in some data
    await page.getByLabel('API Token').fill('test-token')
    await page.getByLabel('API Secret').fill('test-secret')

    // Cancel
    await page.getByRole('button', { name: 'Cancel' }).click()

    // Open again - fields should be empty
    await page.getByRole('button', { name: 'Configure Discogs API' }).click()
    await expect(page.getByLabel('API Token')).toHaveValue('')
    await expect(page.getByLabel('API Secret')).toHaveValue('')
  })

  test('should show loading states', async ({ page }) => {
    // Add delayed responses
    await page.route('/api/v1/config/api-keys', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 1000))
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      })
    })

    await page.route('/api/v1/config/preferences', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 1000))
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          email_notifications: false,
          notification_frequency: 'immediate',
          currency: 'EUR',
          default_search_platform: 'discogs',
        }),
      })
    })

    await page.goto('/settings')

    // Should show loading spinners
    const spinners = page.locator('.animate-spin')
    await expect(spinners).toHaveCount(2) // One for each section
  })
})

test.describe('Settings Page - Mobile View', () => {
  test.use({ viewport: { width: 375, height: 667 } })

  test.beforeEach(async ({ page }) => {
    await setupAuthentication(page)

    // Mock minimal data
    await page.route('/api/v1/config/api-keys', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { service: 'discogs', has_key: false },
          { service: 'ebay', has_key: false },
        ]),
      })
    })

    await page.route('/api/v1/config/preferences', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          email_notifications: false,
          notification_frequency: 'immediate',
          currency: 'USD',
          default_search_platform: 'both',
        }),
      })
    })
  })

  test('should display settings correctly on mobile', async ({ page }) => {
    await page.goto('/settings')

    // Header should be visible
    await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible()

    // Cards should stack vertically
    const cards = page.locator('.card')
    await expect(cards).toHaveCount(2) // API Keys and Preferences

    // Configure buttons should be full width on mobile
    const configureButton = page.getByRole('button', { name: 'Configure Discogs API' })
    const buttonBox = await configureButton.boundingBox()

    if (buttonBox) {
      // Button should span most of the card width
      expect(buttonBox.width).toBeGreaterThan(300)
    }
  })

  test('should handle form inputs on mobile', async ({ page }) => {
    await page.goto('/settings')

    // Open configuration form
    await page.getByRole('button', { name: 'Configure Discogs API' }).tap()

    // Input fields should be accessible
    const tokenInput = page.getByLabel('API Token')
    await expect(tokenInput).toBeVisible()

    // Keyboard should work properly
    await tokenInput.tap()
    await page.keyboard.type('mobile-test-token')
    await expect(tokenInput).toHaveValue('mobile-test-token')

    // Buttons should be tappable
    const saveButton = page.getByRole('button', { name: /save.*discogs/i })
    const saveButtonBox = await saveButton.boundingBox()

    if (saveButtonBox) {
      // Ensure minimum tap target size
      expect(saveButtonBox.height).toBeGreaterThanOrEqual(44)
    }
  })
})

// Cross-browser specific tests
test.describe('Settings Page - Browser Compatibility', () => {
  test('should handle form autofill correctly', async ({ page }) => {
    await setupAuthentication(page)

    // Mock API responses
    await page.route('/api/v1/config/api-keys', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { service: 'discogs', has_key: false },
          { service: 'ebay', has_key: false },
        ]),
      })
    })

    await page.route('/api/v1/config/preferences', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          email_notifications: false,
          notification_frequency: 'immediate',
          currency: 'USD',
          default_search_platform: 'both',
        }),
      })
    })

    await page.goto('/settings')

    // Open configuration
    await page.getByRole('button', { name: 'Configure Discogs API' }).click()

    // Check that password fields have correct autocomplete attributes
    const secretInput = page.getByLabel('API Secret')
    await expect(secretInput).toHaveAttribute('type', 'password')

    // Browser-specific behavior might vary, but fields should be fillable
    await secretInput.fill('test-secret')
    await expect(secretInput).toHaveValue('test-secret')
  })
})
