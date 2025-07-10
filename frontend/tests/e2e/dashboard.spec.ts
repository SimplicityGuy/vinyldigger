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

test.describe('Dashboard Page', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthentication(page)

    // Mock dashboard data
    await page.route('/api/v1/collections/status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: '123',
          item_count: 150,
          last_sync_at: new Date(Date.now() - 3600000).toISOString(), // 1 hour ago
        }),
      })
    })

    await page.route('/api/v1/searches', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: '1',
            name: 'Blue Note Jazz',
            query: 'blue note jazz vinyl',
            platform: 'both',
            is_active: true,
            check_interval_hours: 24,
            last_checked_at: new Date(Date.now() - 7200000).toISOString(), // 2 hours ago
            created_at: new Date(Date.now() - 86400000).toISOString(),
            updated_at: new Date(Date.now() - 7200000).toISOString(),
            filters: {},
          },
          {
            id: '2',
            name: 'Rare Soul 45s',
            query: 'soul 45 rpm',
            platform: 'ebay',
            is_active: false,
            check_interval_hours: 12,
            last_checked_at: null,
            created_at: new Date(Date.now() - 172800000).toISOString(),
            updated_at: new Date(Date.now() - 172800000).toISOString(),
            filters: { format: '45 RPM' },
          },
        ]),
      })
    })

    await page.route('/api/v1/config/api-keys', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            service: 'discogs',
            has_key: true,
            created_at: new Date(Date.now() - 604800000).toISOString(), // 7 days ago
            updated_at: new Date(Date.now() - 604800000).toISOString(),
          },
          {
            service: 'ebay',
            has_key: false,
          },
        ]),
      })
    })
  })

  test('should display all dashboard sections', async ({ page }) => {
    await page.goto('/dashboard')

    // Check header
    await expect(page.getByText('Dashboard')).toBeVisible()
    await expect(page.getByText('Overview of your VinylDigger activity')).toBeVisible()

    // Check collection status
    await expect(page.getByText('Collection Status')).toBeVisible()
    await expect(page.getByText('150')).toBeVisible() // item count
    await expect(page.getByText('Items in collection')).toBeVisible()
    await expect(page.getByText('Last synced:')).toBeVisible()

    // Check recent searches
    await expect(page.getByText('Recent Searches')).toBeVisible()
    await expect(page.getByText('Blue Note Jazz')).toBeVisible()
    await expect(page.getByText('Rare Soul 45s')).toBeVisible()

    // Check API keys section
    await expect(page.getByText('API Keys')).toBeVisible()
    await expect(page.getByText('Discogs')).toBeVisible()
    await expect(page.getByText('Configured')).toBeVisible()
    await expect(page.getByText('eBay')).toBeVisible()
    await expect(page.getByText('Not configured')).toBeVisible()
  })

  test('should show sync collection button when Discogs username exists', async ({ page }) => {
    await page.goto('/dashboard')

    const syncButton = page.getByRole('button', { name: 'Sync Collection' })
    await expect(syncButton).toBeVisible()
    await expect(syncButton).toBeEnabled()
  })

  test('should handle collection sync', async ({ page }) => {
    await page.goto('/dashboard')

    // Mock sync collection API
    await page.route('/api/v1/collections/sync', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Sync started' }),
      })
    })

    // Click sync button
    await page.getByRole('button', { name: 'Sync Collection' }).click()

    // Should show success toast
    await expect(page.getByText('Collection sync started')).toBeVisible()
    await expect(page.getByText('Your collection is being synced in the background')).toBeVisible()
  })

  test('should navigate to searches page when viewing all searches', async ({ page }) => {
    await page.goto('/dashboard')

    await page.getByRole('button', { name: 'View all' }).click()

    await expect(page).toHaveURL('/searches')
  })

  test('should navigate to settings page from API keys section', async ({ page }) => {
    await page.goto('/dashboard')

    // Find the link in the API keys section
    const configureLink = page.getByRole('link', { name: 'Configure in settings →' })
    await configureLink.click()

    await expect(page).toHaveURL('/settings')
  })

  test('should display loading states correctly', async ({ page }) => {
    // Remove route mocks to see loading states
    await page.unroute('/api/v1/collections/status')
    await page.unroute('/api/v1/searches')
    await page.unroute('/api/v1/config/api-keys')

    // Add slow responses
    await page.route('/api/v1/collections/status', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 1000))
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ id: '123', item_count: 0 }),
      })
    })

    await page.goto('/dashboard')

    // Should show loading spinners
    const spinners = page.locator('.animate-spin')
    await expect(spinners).toHaveCount(3) // One for each section
  })

  test('should handle API errors gracefully', async ({ page }) => {
    // Mock error responses
    await page.route('/api/v1/collections/status', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Internal server error' }),
      })
    })

    await page.goto('/dashboard')

    // Should still show the page without crashing
    await expect(page.getByText('Dashboard')).toBeVisible()
  })
})

test.describe('Dashboard Mobile View', () => {
  test.use({ viewport: { width: 375, height: 667 } })

  test.beforeEach(async ({ page }) => {
    await setupAuthentication(page)

    // Mock minimal data for mobile view
    await page.route('/api/v1/collections/status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ id: '123', item_count: 150 }),
      })
    })

    await page.route('/api/v1/searches', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      })
    })

    await page.route('/api/v1/config/api-keys', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      })
    })
  })

  test('should display dashboard correctly on mobile', async ({ page }) => {
    await page.goto('/dashboard')

    // Check that layout is responsive
    await expect(page.getByText('Dashboard')).toBeVisible()

    // Cards should stack vertically on mobile
    const cards = page.locator('.grid > .card')
    const firstCard = cards.first()
    const secondCard = cards.nth(1)

    // Get bounding boxes to verify vertical stacking
    const firstBox = await firstCard.boundingBox()
    const secondBox = await secondCard.boundingBox()

    if (firstBox && secondBox) {
      // Second card should be below first card
      expect(secondBox.y).toBeGreaterThan(firstBox.y + firstBox.height)
    }
  })
})

// Skip navigation test
test('should allow keyboard users to skip to main content', async ({ page }) => {
  await setupAuthentication(page)
  await page.goto('/dashboard')

  // Focus on skip link by pressing Tab
  await page.keyboard.press('Tab')

  // The skip link should be visible when focused
  const skipLink = page.getByText('Skip to main content')
  await expect(skipLink).toBeFocused()
  await expect(skipLink).toBeVisible()

  // Click the skip link
  await skipLink.click()

  // Main content should be focused
  const mainContent = page.locator('#main-content')
  await expect(mainContent).toBeFocused()
})
