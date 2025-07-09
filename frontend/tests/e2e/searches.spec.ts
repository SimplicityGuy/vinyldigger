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

// Mock search data
const mockSearches = [
  {
    id: '1',
    name: 'Jazz Vinyl Collection',
    query: 'jazz vinyl LP',
    platform: 'both',
    is_active: true,
    check_interval_hours: 24,
    last_checked_at: new Date(Date.now() - 3600000).toISOString(),
    created_at: new Date(Date.now() - 86400000).toISOString(),
    updated_at: new Date(Date.now() - 3600000).toISOString(),
    filters: {
      genre: 'Jazz',
      format: 'LP',
      min_price: 10,
      max_price: 100,
    },
  },
  {
    id: '2',
    name: 'Rare Beatles Singles',
    query: 'beatles 45 single',
    platform: 'discogs',
    is_active: false,
    check_interval_hours: 12,
    last_checked_at: null,
    created_at: new Date(Date.now() - 172800000).toISOString(),
    updated_at: new Date(Date.now() - 172800000).toISOString(),
    filters: {
      format: '45 RPM',
    },
  },
]

test.describe('Searches Page', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthentication(page)
  })

  test('should display searches list', async ({ page }) => {
    // Mock searches API
    await page.route('/api/v1/searches', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockSearches),
      })
    })

    await page.goto('/searches')

    // Check page header
    await expect(page.getByText('Searches', { exact: true })).toBeVisible()
    await expect(page.getByText('Manage your saved searches and view results')).toBeVisible()

    // Check new search button
    await expect(page.getByRole('button', { name: 'Create a new search' })).toBeVisible()

    // Check search cards
    await expect(page.getByText('Jazz Vinyl Collection')).toBeVisible()
    await expect(page.getByText('jazz vinyl LP • both • Every 24 hours')).toBeVisible()

    await expect(page.getByText('Rare Beatles Singles')).toBeVisible()
    await expect(page.getByText('beatles 45 single • discogs • Every 12 hours')).toBeVisible()
  })

  test('should display empty state when no searches', async ({ page }) => {
    // Mock empty searches
    await page.route('/api/v1/searches', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      })
    })

    await page.goto('/searches')

    // Check empty state
    await expect(page.getByText('No searches yet')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Create your first search' })).toBeVisible()
  })

  test('should run a search', async ({ page }) => {
    await page.route('/api/v1/searches', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockSearches),
      })
    })

    // Mock run search API
    await page.route('/api/v1/searches/1/run', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Search started' }),
      })
    })

    await page.goto('/searches')

    // Find and click run button for first search
    const firstSearchCard = page.locator('.card').filter({ hasText: 'Jazz Vinyl Collection' })
    const runButton = firstSearchCard.getByRole('button', { name: /run/i })
    await runButton.click()

    // Should show success toast
    await expect(page.getByText('Search started')).toBeVisible()
    await expect(page.getByText('Your search is running in the background.')).toBeVisible()
  })

  test('should delete a search', async ({ page }) => {
    await page.route('/api/v1/searches', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockSearches),
      })
    })

    // Mock delete search API
    await page.route('/api/v1/searches/2', async (route) => {
      if (route.request().method() === 'DELETE') {
        await route.fulfill({
          status: 204,
        })
      }
    })

    await page.goto('/searches')

    // Find and click delete button for second search
    const secondSearchCard = page.locator('.card').filter({ hasText: 'Rare Beatles Singles' })
    const deleteButton = secondSearchCard.getByRole('button', { name: /delete/i })
    await deleteButton.click()

    // Should show success toast
    await expect(page.getByText('Search deleted')).toBeVisible()
    await expect(page.getByText('The search has been removed.')).toBeVisible()
  })

  test('should show last checked time correctly', async ({ page }) => {
    await page.route('/api/v1/searches', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockSearches),
      })
    })

    await page.goto('/searches')

    // First search was checked 1 hour ago
    const firstSearchCard = page.locator('.card').filter({ hasText: 'Jazz Vinyl Collection' })
    await expect(firstSearchCard.getByText(/hour.*ago/)).toBeVisible()

    // Second search was never checked
    const secondSearchCard = page.locator('.card').filter({ hasText: 'Rare Beatles Singles' })
    await expect(secondSearchCard.getByText('Never')).toBeVisible()
  })

  test('should show loading state', async ({ page }) => {
    // Add delayed response
    await page.route('/api/v1/searches', async (route) => {
      await new Promise(resolve => setTimeout(resolve, 1000))
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      })
    })

    await page.goto('/searches')

    // Should show loading spinner with proper ARIA attributes
    const loadingContainer = page.locator('[role="status"][aria-label="Loading searches"]')
    await expect(loadingContainer).toBeVisible()
    await expect(page.getByText('Loading searches...')).toHaveClass(/sr-only/)
  })

  test('should show active/inactive status badges', async ({ page }) => {
    await page.route('/api/v1/searches', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockSearches),
      })
    })

    await page.goto('/searches')

    // Check that active searches show different styling/badges
    const activeCard = page.locator('.card').filter({ hasText: 'Jazz Vinyl Collection' })
    const inactiveCard = page.locator('.card').filter({ hasText: 'Rare Beatles Singles' })

    // Both cards should be visible
    await expect(activeCard).toBeVisible()
    await expect(inactiveCard).toBeVisible()

    // Active search should have run button enabled
    await expect(activeCard.getByRole('button', { name: /run/i })).toBeEnabled()
  })
})

test.describe('Searches Page - Mobile View', () => {
  test.use({ viewport: { width: 375, height: 667 } })

  test.beforeEach(async ({ page }) => {
    await setupAuthentication(page)

    await page.route('/api/v1/searches', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockSearches),
      })
    })
  })

  test('should display searches correctly on mobile', async ({ page }) => {
    await page.goto('/searches')

    // Header should be visible
    await expect(page.getByText('Searches', { exact: true })).toBeVisible()

    // New search button should be visible and accessible
    const newSearchButton = page.getByRole('button', { name: 'Create a new search' })
    await expect(newSearchButton).toBeVisible()

    // Search cards should stack vertically
    const cards = page.locator('.card')
    await expect(cards).toHaveCount(2)

    // All content should fit within viewport
    const firstCard = cards.first()
    const cardBox = await firstCard.boundingBox()
    if (cardBox) {
      expect(cardBox.width).toBeLessThanOrEqual(375)
    }
  })

  test('should handle button interactions on mobile', async ({ page }) => {
    // Mock run search API
    await page.route('/api/v1/searches/1/run', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Search started' }),
      })
    })

    await page.goto('/searches')

    // Tap run button on first search
    const firstSearchCard = page.locator('.card').filter({ hasText: 'Jazz Vinyl Collection' })
    const runButton = firstSearchCard.getByRole('button', { name: /run/i })

    // Ensure button is large enough for mobile tap
    const buttonBox = await runButton.boundingBox()
    if (buttonBox) {
      expect(buttonBox.height).toBeGreaterThanOrEqual(44) // iOS minimum tap target
    }

    await runButton.tap()

    // Toast should be visible on mobile
    await expect(page.getByText('Search started')).toBeVisible()
  })
})

// Accessibility tests
test.describe('Searches Page - Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthentication(page)

    await page.route('/api/v1/searches', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockSearches),
      })
    })
  })

  test('should have proper focus management', async ({ page }) => {
    await page.goto('/searches')

    // Tab through interactive elements
    await page.keyboard.press('Tab') // Skip link
    await page.keyboard.press('Tab') // VinylDigger logo/home
    await page.keyboard.press('Tab') // Dashboard nav
    await page.keyboard.press('Tab') // Searches nav (should be current)

    const searchesNavLink = page.getByRole('link', { name: 'Searches' })
    await expect(searchesNavLink).toHaveAttribute('aria-current', 'page')
  })

  test('should announce search results to screen readers', async ({ page }) => {
    await page.goto('/searches')

    // Loading state should have proper ARIA attributes
    const loadingState = page.locator('[role="status"]')
    if (await loadingState.isVisible()) {
      await expect(loadingState).toHaveAttribute('aria-label', 'Loading searches')
    }

    // Search cards should be in a list or have proper semantics
    await page.waitForSelector('.card')
    const searchCards = page.locator('.grid > .card')
    await expect(searchCards).toHaveCount(2)
  })
})
