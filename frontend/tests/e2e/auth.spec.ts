import { test, expect, type Page } from '@playwright/test'
import { randomBytes } from 'crypto'
import { CI_TIMEOUT } from './test-config'

// Helper to generate unique test data
const generateTestUser = () => ({
  email: `test-${randomBytes(8).toString('hex')}@example.com`,
  password: 'TestPassword123!',
})

// Helper to fill login form
async function fillLoginForm(page: Page, email: string, password: string) {
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(password)
}

// Helper to fill registration form
async function fillRegistrationForm(
  page: Page,
  email: string,
  password: string
) {
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(password)
}

test.describe('Authentication Flow', () => {
  test.describe('Login Page', () => {
    test('should display all login page elements', async ({ page }) => {
      await page.goto('/login')

      // Check main elements
      await expect(page.getByText('Welcome to VinylDigger')).toBeVisible()
      await expect(page.getByText('Sign in to your account to continue')).toBeVisible()

      // Check form elements
      await expect(page.getByLabel('Email')).toBeVisible()
      await expect(page.getByLabel('Password')).toBeVisible()
      await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible()

      // Check registration link
      await expect(page.getByText("Don't have an account?")).toBeVisible()
      await expect(page.getByRole('link', { name: 'Sign up' })).toBeVisible()

      // Check decorative elements have proper ARIA attributes
      const logo = page.locator('[aria-hidden="true"] svg')
      await expect(logo).toBeVisible()
    })

    test('should show validation errors for empty form submission', async ({ page }) => {
      await page.goto('/login')

      // Try to submit empty form
      await page.getByRole('button', { name: 'Sign in' }).click()

      // Form should not submit and we should still be on login page
      await expect(page).toHaveURL('/login')

      // Check that error messages are shown (any validation error)
      await expect(page.locator('.text-destructive').first()).toBeVisible()
    })

    test('should show validation error for invalid email', async ({ page }) => {
      await page.goto('/login')

      await page.getByLabel('Email').fill('invalid-email')
      await page.getByLabel('Password').fill('validpassword123')
      await page.getByRole('button', { name: 'Sign in' }).click()

      // Form should not submit and we should still be on login page
      await expect(page).toHaveURL('/login')

      // Check that error message is shown under email field
      const emailError = page.locator('input[type="email"] ~ .text-destructive')
      await expect(emailError).toBeVisible({ timeout: CI_TIMEOUT })
    })

    test('should navigate to register page when clicking sign up', async ({ page }) => {
      await page.goto('/login')

      await page.getByRole('link', { name: 'Sign up' }).click()

      await expect(page).toHaveURL('/register')
      await expect(page.getByText('Create an account')).toBeVisible()
    })

    test('should show loading state during login', async ({ page }) => {
      await page.goto('/login')

      const testUser = generateTestUser()
      await fillLoginForm(page, testUser.email, testUser.password)

      // Mock a successful but slow API response
      let resolveLogin: () => void
      const loginPromise = new Promise<void>(resolve => {
        resolveLogin = resolve
      })

      await page.route('/api/v1/auth/login', async (route) => {
        await loginPromise
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            access_token: 'mock-token',
            refresh_token: 'mock-refresh',
            token_type: 'bearer',
          }),
        })
      })

      const submitButton = page.getByRole('button', { name: 'Sign in' })

      // Click the button
      const clickPromise = submitButton.click()

      // Check that button shows loading state
      await expect(submitButton).toHaveAttribute('aria-busy', 'true', { timeout: 1000 })

      // Resolve the login to complete the test
      resolveLogin!()
      await clickPromise
    })
  })

  test.describe('Registration Page', () => {
    test('should display all registration page elements', async ({ page }) => {
      await page.goto('/register')

      // Check main elements
      await expect(page.getByText('Create an account')).toBeVisible()
      await expect(page.getByText('Start discovering vinyl records today')).toBeVisible()

      // Check form elements
      await expect(page.getByLabel('Email')).toBeVisible()
      await expect(page.getByLabel('Password')).toBeVisible()
      await expect(page.getByRole('button', { name: 'Create account' })).toBeVisible()

      // Check login link
      await expect(page.getByText('Already have an account?')).toBeVisible()
      await expect(page.getByRole('link', { name: 'Sign in' })).toBeVisible()
    })

    test('should show validation errors for empty form submission', async ({ page }) => {
      await page.goto('/register')

      // Try to submit empty form
      await page.getByRole('button', { name: 'Create account' }).click()

      // Form should not submit and we should still be on register page
      await expect(page).toHaveURL('/register')

      // Check that error messages are shown
      await expect(page.locator('.text-destructive').first()).toBeVisible()
    })

    test('should successfully register with valid data', async ({ page }) => {
      await page.goto('/register')

      const testUser = generateTestUser()
      await fillRegistrationForm(page, testUser.email, testUser.password)

      // Mock successful registration
      await page.route('/api/v1/auth/register', async (route) => {
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            id: '123',
            email: testUser.email,
          }),
        })
      })

      await page.getByRole('button', { name: 'Create account' }).click()

      // Should redirect to login page
      await expect(page).toHaveURL('/login')

      // Should show success toast
      await expect(page.getByText('Registration successful').first()).toBeVisible()
      await expect(page.getByText('Please log in with your new account.').first()).toBeVisible()
    })

    test('should navigate to login page when clicking sign in', async ({ page }) => {
      await page.goto('/register')

      await page.getByRole('link', { name: 'Sign in' }).click()

      await expect(page).toHaveURL('/login')
      await expect(page.getByText('Welcome to VinylDigger')).toBeVisible()
    })
  })

  test.describe('Authentication Redirects', () => {
    test('should redirect to login when accessing protected route while unauthenticated', async ({ page }) => {
      // Clear any existing auth tokens
      await page.context().clearCookies()

      // Try to access protected routes
      const protectedRoutes = ['/dashboard', '/searches', '/settings']

      for (const route of protectedRoutes) {
        await page.goto(route)
        await expect(page).toHaveURL('/login')
      }
    })

    test('should redirect to dashboard when accessing auth pages while authenticated', async ({ page }) => {
      // Mock authentication
      await page.addInitScript(() => {
        window.sessionStorage.setItem('access_token', 'mock-access-token')
        window.localStorage.setItem('refresh_token', JSON.stringify({
          token: 'mock-refresh-token',
          expiry: Date.now() + 86400000, // 24 hours
        }))
      })

      // Mock API response for user data
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

      // Try to access auth pages
      await page.goto('/login')
      await expect(page).toHaveURL('/dashboard')

      await page.goto('/register')
      await expect(page).toHaveURL('/dashboard')
    })
  })

  test.describe('Logout Flow', () => {
    test.beforeEach(async ({ page }) => {
      // Set up authenticated state
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
    })

    test('should successfully logout and redirect to login', async ({ page }) => {
      await page.goto('/dashboard')

      // Should show user email in header
      await expect(page.getByText('test@example.com')).toBeVisible()

      // Click logout button
      await page.getByRole('button', { name: 'Logout from VinylDigger' }).click()

      // Should redirect to login
      await expect(page).toHaveURL('/login')

      // Should show logout success toast
      const toast = page.locator('[role="status"]').filter({ hasText: 'Logged out' }).first()
      await expect(toast).toBeVisible({ timeout: CI_TIMEOUT })
      await expect(page.getByText('You have been logged out successfully.').first()).toBeVisible({ timeout: CI_TIMEOUT })

      // Should clear auth tokens
      const sessionToken = await page.evaluate(() => window.sessionStorage.getItem('access_token'))
      const refreshToken = await page.evaluate(() => window.localStorage.getItem('refresh_token'))
      expect(sessionToken).toBeNull()
      expect(refreshToken).toBeNull()
    })
  })
})

// Mobile-specific tests
test.describe('Mobile Authentication', () => {
  test.use({ viewport: { width: 375, height: 667 } }) // iPhone viewport

  test('should display login page correctly on mobile', async ({ page }) => {
    await page.goto('/login')

    // Check that card is full width on mobile
    const card = page.locator('.max-w-md')
    await expect(card).toBeVisible()

    // Check all elements are visible and properly sized
    await expect(page.getByText('Welcome to VinylDigger')).toBeVisible()
    await expect(page.getByLabel('Email')).toBeVisible()
    await expect(page.getByLabel('Password')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible()
  })

  test('should handle form submission on mobile', async ({ page }) => {
    await page.goto('/login')

    const testUser = generateTestUser()
    await fillLoginForm(page, testUser.email, testUser.password)

    // Mock API response
    await page.route('/api/v1/auth/login', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Invalid credentials',
        }),
      })
    })

    await page.getByRole('button', { name: 'Sign in' }).click()

    // Toast should be visible on mobile
    const toast = page.locator('[role="status"]').filter({ hasText: 'Login failed' }).first()
    await expect(toast).toBeVisible({ timeout: CI_TIMEOUT })
    await expect(page.getByText('Invalid credentials').first()).toBeVisible({ timeout: CI_TIMEOUT })
  })
})
