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

    // Check OAuth section
    await expect(page.getByText('Platform Authorizations')).toBeVisible()
    await expect(page.getByText('Authorize VinylDigger to access your accounts on different platforms')).toBeVisible()

    // Check Discogs OAuth
    await expect(page.getByText('Discogs').first()).toBeVisible()

    // Check eBay OAuth
    await expect(page.getByText('eBay').first()).toBeVisible()

    // Check Preferences section
    await expect(page.getByText('Preferences')).toBeVisible()
    await expect(page.getByText('Customize your VinylDigger experience')).toBeVisible()
  })



  test('should display current preferences', async ({ page }) => {
    await page.goto('/settings')

    // Check notifications section exists
    await expect(page.getByText('Notifications')).toBeVisible({ timeout: CI_TIMEOUT })
    await expect(page.getByText('Configure how you want to be notified')).toBeVisible({ timeout: CI_TIMEOUT })

    // Check email notifications checkbox
    await expect(page.getByText('Email Notifications')).toBeVisible({ timeout: CI_TIMEOUT })
    await expect(page.getByText('Receive email alerts when new matches are found')).toBeVisible({ timeout: CI_TIMEOUT })

    // Check that the checkbox is checked (based on mock data)
    const checkbox = page.getByRole('checkbox')
    await expect(checkbox).toBeChecked({ timeout: CI_TIMEOUT })
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
    await expect(spinners.first()).toBeVisible({ timeout: CI_TIMEOUT })
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
    await expect(cards.first()).toBeVisible({ timeout: CI_TIMEOUT })

    // OAuth section should be visible
    await expect(page.getByText('Platform Authorizations')).toBeVisible({ timeout: CI_TIMEOUT })
    await expect(page.getByText('Preferences')).toBeVisible({ timeout: CI_TIMEOUT })
  })

})
