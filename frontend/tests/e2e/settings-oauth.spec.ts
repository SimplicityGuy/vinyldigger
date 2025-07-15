import { test, expect } from '@playwright/test'
import type { Page, Route } from '@playwright/test'
import { CI_TIMEOUT } from './test-config'

// Login helper
async function loginHelper(page: Page) {
  // Mock auth endpoints
  await page.route('/api/v1/auth/login', async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        access_token: 'test-access-token',
        refresh_token: 'test-refresh-token',
        token_type: 'bearer',
      }),
    })
  })

  await page.route('/api/v1/auth/me', async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'test-user-id',
        email: 'test@example.com',
        is_active: true,
        created_at: new Date().toISOString(),
      }),
    })
  })

  // Perform login
  await page.goto('/login')
  await page.getByLabel('Email').fill('test@example.com')
  await page.getByLabel('Password').fill('password123')
  await page.getByRole('button', { name: 'Sign in' }).click()
  await page.waitForURL('/dashboard')
}

test.describe('Settings Page OAuth', () => {
  test.beforeEach(async ({ page }) => {
    // Login first
    await loginHelper(page)

    // Mock OAuth status endpoints - correct API paths
    await page.route('/api/v1/oauth/status/discogs', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          provider: 'DISCOGS',
          is_configured: true,
          is_authorized: false,
          username: null,
        }),
      })
    })

    await page.route('/api/v1/oauth/status/ebay', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          provider: 'EBAY',
          is_configured: true,
          is_authorized: false,
          username: null,
        }),
      })
    })

    // Navigate to settings
    await page.goto('/settings')
  })

  test('should display OAuth authorization buttons', async ({ page }) => {
    // Check Discogs OAuth section
    await expect(page.getByText('Discogs').first()).toBeVisible({ timeout: CI_TIMEOUT })
    await expect(page.getByRole('button', { name: 'Connect Discogs Account' })).toBeVisible({ timeout: CI_TIMEOUT })

    // Check eBay OAuth section
    await expect(page.getByText('eBay').first()).toBeVisible({ timeout: CI_TIMEOUT })
    await expect(page.getByRole('button', { name: 'Connect eBay Account' })).toBeVisible({ timeout: CI_TIMEOUT })
  })

  test('should initiate Discogs OAuth flow', async ({ page }) => {
    // Mock OAuth authorization endpoint - correct API path
    await page.route('/api/v1/oauth/authorize/discogs', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          authorization_url: 'https://discogs.com/oauth/authorize?oauth_token=test',
          state: 'test-state',
        }),
      })
    })

    // Click authorize button
    const authorizeButton = page.getByRole('button', { name: 'Connect Discogs Account' })
    await authorizeButton.click()

    // Wait for the authorization to complete
    await page.waitForTimeout(500)
  })

  test('should show authorized status when connected', async ({ page }) => {
    // Mock authorized status
    await page.route('/api/v1/oauth/status/discogs', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          provider: 'DISCOGS',
          is_configured: true,
          is_authorized: true,
          username: 'testuser',
        }),
      })
    })

    await page.reload()

    // Should show connected status
    await expect(page.getByText('Connected as testuser')).toBeVisible({ timeout: CI_TIMEOUT })
    await expect(page.getByRole('button', { name: 'Revoke Access' })).toBeVisible({ timeout: CI_TIMEOUT })
  })

  test('should handle Discogs verification flow', async ({ page }) => {
    // Mock OAuth authorization endpoint
    await page.route('/api/v1/oauth/authorize/discogs', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          authorization_url: 'https://discogs.com/oauth/authorize?oauth_token=test',
          state: 'test-state-123',
        }),
      })
    })

    // Mock verification endpoint
    await page.route('/api/v1/oauth/verify/discogs', async (route) => {
      const body = await route.request().postDataJSON()
      if (body.state === 'test-state-123' && body.verification_code === 'ABC123') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            message: 'Successfully authorized Discogs access!',
            username: 'testuser',
          }),
        })
      } else {
        await route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({
            detail: 'Invalid verification code',
          }),
        })
      }
    })

    // Click authorize button
    await page.getByRole('button', { name: 'Connect Discogs Account' }).click()

    // Wait for verification input to appear
    await expect(page.getByPlaceholder('Enter verification code')).toBeVisible({ timeout: CI_TIMEOUT })

    // Enter verification code
    await page.getByPlaceholder('Enter verification code').fill('ABC123')
    await page.getByRole('button', { name: 'Verify' }).click()

    // Should show success toast
    await expect(page.getByText('Success!').first()).toBeVisible({ timeout: CI_TIMEOUT })
    await expect(page.getByText('Connected to Discogs as testuser')).toBeVisible({ timeout: CI_TIMEOUT })
  })

  test('should revoke OAuth access', async ({ page }) => {
    // Mock authorized status
    await page.route('/api/v1/oauth/status/ebay', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          provider: 'EBAY',
          is_configured: true,
          is_authorized: true,
          username: 'ebayuser',
        }),
      })
    })

    // Mock revoke endpoint
    await page.route('/api/v1/oauth/revoke/ebay', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'Successfully revoked eBay access.',
        }),
      })
    })

    await page.reload()

    // Should show connected status
    await expect(page.getByText('Connected as ebayuser')).toBeVisible({ timeout: 10000 })

    // Click revoke in confirmation dialog
    page.on('dialog', dialog => dialog.accept())

    // Click revoke button
    await page.getByRole('button', { name: 'Revoke Access' }).click() // There's only one visible

    // Wait for the status to update
    await page.waitForTimeout(1000)

    // After revoke, the button should change back to Connect
    await expect(page.getByRole('button', { name: 'Connect eBay Account' })).toBeVisible({ timeout: CI_TIMEOUT })
  })
})
