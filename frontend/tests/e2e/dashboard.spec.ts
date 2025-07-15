import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import { CI_TIMEOUT } from './test-config'

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

    await page.route('/api/v1/wantlist/status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: '124',
          item_count: 25,
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
            last_run_at: new Date(Date.now() - 7200000).toISOString(), // 2 hours ago
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
            last_run_at: null,
            created_at: new Date(Date.now() - 172800000).toISOString(),
            updated_at: new Date(Date.now() - 172800000).toISOString(),
            filters: { format: '45 RPM' },
          },
        ]),
      })
    })

    await page.route('/api/v1/oauth/status/discogs', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          is_configured: true,
          is_authorized: true,
          username: 'testuser',
        }),
      })
    })
  })

  test('should display all dashboard sections', async ({ page }) => {
    await page.goto('/dashboard')

    // Check header
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
    await expect(page.getByText('Overview of your vinyl collection and recent activity')).toBeVisible()

    // Check collection stats
    await expect(page.getByRole('heading', { name: 'Collection' })).toBeVisible()
    await expect(page.getByText('150')).toBeVisible() // item count
    await expect(page.getByText('Records in your collection')).toBeVisible()

    // Check want list stats
    await expect(page.getByRole('heading', { name: 'Want List' })).toBeVisible()

    // Check last sync
    await expect(page.getByRole('heading', { name: 'Last Sync' })).toBeVisible()

    // Check quick actions section
    await expect(page.getByRole('heading', { name: 'Quick Actions' })).toBeVisible()
    await expect(page.getByText('Common tasks to manage your collection')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Sync All' })).toBeVisible()
  })

  test('should show sync collection button when Discogs username exists', async ({ page }) => {
    await page.goto('/dashboard')

    const syncButton = page.getByRole('button', { name: 'Sync All' })
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
    await page.getByRole('button', { name: 'Sync All' }).click()

    // Should show success toast
    await expect(page.getByText('Sync started')).toBeVisible({ timeout: CI_TIMEOUT })
    await expect(page.getByText('Your collection and want list are being synced with Discogs.')).toBeVisible({ timeout: CI_TIMEOUT })
  })

  test('should navigate to searches page from navigation', async ({ page }) => {
    await page.goto('/dashboard')

    // Navigate using the main navigation
    await page.getByRole('link', { name: 'Searches' }).click()

    await expect(page).toHaveURL('/searches')
  })

  test('should navigate to settings page from dashboard links', async ({ page }) => {
    await page.goto('/dashboard')

    // Find the Settings link
    const settingsLink = page.getByRole('link', { name: 'Settings' }).first()
    await settingsLink.click()

    await expect(page).toHaveURL('/settings')
  })

  test('should display loading states correctly', async ({ page }) => {
    // Remove route mocks to see loading states
    await page.unroute('/api/v1/collections/status')
    await page.unroute('/api/v1/wantlist/status')
    await page.unroute('/api/v1/searches')
    await page.unroute('/api/v1/oauth/status/discogs')

    // Add slow responses
    await page.route('/api/v1/collections/status', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 1000))
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ id: '123', item_count: 0 }),
      })
    })

    await page.route('/api/v1/wantlist/status', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 1000))
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ id: '124', item_count: 0 }),
      })
    })

    await page.goto('/dashboard')

    // Should show loading spinners
    const spinners = page.locator('.animate-spin')
    await expect(spinners.first()).toBeVisible()
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
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
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

    await page.route('/api/v1/wantlist/status', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ id: '124', item_count: 25 }),
      })
    })

    await page.route('/api/v1/searches', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      })
    })

    await page.route('/api/v1/oauth/status/discogs', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          is_configured: true,
          is_authorized: true,
          username: 'testuser',
        }),
      })
    })
  })

  test('should display dashboard correctly on mobile', async ({ page }) => {
    await page.goto('/dashboard')

    // Check that layout is responsive
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible({ timeout: CI_TIMEOUT })

    // Wait for cards to load
    await expect(page.locator('.card').first()).toBeVisible({ timeout: CI_TIMEOUT })

    // Cards should stack vertically on mobile
    const cards = page.locator('.grid > .card')
    await expect(cards.first()).toBeVisible()
    await expect(cards.nth(1)).toBeVisible()

    // Get bounding boxes to verify vertical stacking
    const firstBox = await cards.first().boundingBox()
    const secondBox = await cards.nth(1).boundingBox()

    if (firstBox && secondBox) {
      // Second card should be below first card
      expect(secondBox.y).toBeGreaterThan(firstBox.y + firstBox.height)
    }
  })
})

// Skip navigation test
test('should allow keyboard users to skip to main content', async ({ page }) => {
  await setupAuthentication(page)

  // Mock dashboard data to ensure page loads properly
  await page.route('/api/v1/collections/status', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ id: '123', item_count: 0 }),
    })
  })

  await page.route('/api/v1/searches', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    })
  })

  await page.route('/api/v1/wantlist/status', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ id: '124', item_count: 0 }),
    })
  })

  await page.route('/api/v1/oauth/status/discogs', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        is_configured: false,
        is_authorized: false,
      }),
    })
  })

  await page.goto('/dashboard')

  // Focus on skip link by pressing Tab
  await page.keyboard.press('Tab')

  // The skip link should be visible when focused
  const skipLink = page.getByText('Skip to main content')
  await expect(skipLink).toBeFocused({ timeout: CI_TIMEOUT })
  await expect(skipLink).toBeVisible({ timeout: CI_TIMEOUT })

  // Click the skip link
  await skipLink.click()

  // Main content should be focused
  const mainContent = page.locator('#main-content')
  await expect(mainContent).toBeFocused({ timeout: CI_TIMEOUT })
})
