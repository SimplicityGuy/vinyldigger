import { test, expect, type Page } from '@playwright/test'
import { randomBytes } from 'crypto'

// Helper to generate unique test data
const generateTestUser = () => ({
  email: `test-${randomBytes(8).toString('hex')}@example.com`,
  password: 'TestPassword123!',
  discogsUsername: `testuser${randomBytes(4).toString('hex')}`,
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
  password: string,
  discogsUsername?: string
) {
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password').fill(password)
  if (discogsUsername) {
    await page.getByLabel('Discogs Username (optional)').fill(discogsUsername)
  }
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

      // Check validation messages
      await expect(page.getByText('Invalid email')).toBeVisible()
      await expect(page.getByText('String must contain at least 8 character(s)')).toBeVisible()
    })

    test('should show validation error for invalid email', async ({ page }) => {
      await page.goto('/login')

      await page.getByLabel('Email').fill('invalid-email')
      await page.getByLabel('Password').fill('validpassword123')
      await page.getByRole('button', { name: 'Sign in' }).click()

      await expect(page.getByText('Invalid email')).toBeVisible()
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

      // Mock slow API response
      await page.route('/api/v1/auth/login', async (route) => {
        await new Promise(resolve => setTimeout(resolve, 1000))
        await route.abort()
      })

      const submitButton = page.getByRole('button', { name: 'Sign in' })
      await submitButton.click()

      // Check loading state
      await expect(submitButton).toBeDisabled()
      await expect(submitButton).toHaveAttribute('aria-busy', 'true')
      await expect(page.getByText('Signing in...')).toBeVisible()
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
      await expect(page.getByLabel('Discogs Username (optional)')).toBeVisible()
      await expect(page.getByRole('button', { name: 'Create account' })).toBeVisible()

      // Check login link
      await expect(page.getByText('Already have an account?')).toBeVisible()
      await expect(page.getByRole('link', { name: 'Sign in' })).toBeVisible()
    })

    test('should show validation errors for empty form submission', async ({ page }) => {
      await page.goto('/register')

      // Try to submit empty form
      await page.getByRole('button', { name: 'Create account' }).click()

      // Check validation messages
      await expect(page.getByText('Invalid email')).toBeVisible()
      await expect(page.getByText('String must contain at least 8 character(s)')).toBeVisible()
    })

    test('should successfully register with valid data', async ({ page }) => {
      await page.goto('/register')

      const testUser = generateTestUser()
      await fillRegistrationForm(page, testUser.email, testUser.password, testUser.discogsUsername)

      // Mock successful registration
      await page.route('/api/v1/auth/register', async (route) => {
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            id: '123',
            email: testUser.email,
            discogs_username: testUser.discogsUsername,
          }),
        })
      })

      await page.getByRole('button', { name: 'Create account' }).click()

      // Should redirect to login page
      await expect(page).toHaveURL('/login')

      // Should show success toast
      await expect(page.getByText('Registration successful')).toBeVisible()
      await expect(page.getByText('Please log in with your new account.')).toBeVisible()
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
      await expect(page.getByText('Logged out')).toBeVisible()
      await expect(page.getByText('You have been logged out successfully.')).toBeVisible()

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
    await expect(page.getByText('Login failed')).toBeVisible()
    await expect(page.getByText('Invalid credentials')).toBeVisible()
  })
})
