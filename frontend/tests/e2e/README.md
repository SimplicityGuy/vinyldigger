# VinylDigger E2E Tests

Comprehensive end-to-end tests for VinylDigger using Playwright.

## Test Coverage

### Authentication Flow (`auth.spec.ts`)
- **Login Page**: Form validation, navigation, loading states, error handling
- **Registration Page**: Form submission, validation, success flows
- **Authentication Redirects**: Protected routes, authenticated redirects
- **Logout Flow**: Token cleanup, navigation
- **Mobile Views**: Responsive design on mobile devices

### Dashboard Page (`dashboard.spec.ts`)
- **Data Display**: Collection status, recent searches, API keys
- **Interactions**: Sync collection, navigation to other pages
- **Loading States**: Proper loading indicators
- **Error Handling**: Graceful error states
- **Accessibility**: Skip navigation, focus management

### Searches Page (`searches.spec.ts`)
- **Search Management**: List, create, run, delete searches
- **Empty States**: Proper messaging when no searches
- **Real-time Updates**: Last checked times, status badges
- **Mobile Optimization**: Touch interactions, responsive layout
- **Accessibility**: Screen reader announcements, focus management

### Settings Page (`settings.spec.ts`)
- **API Configuration**: Discogs and eBay API key management
- **Preferences Display**: User settings and preferences
- **Form Handling**: Validation, error states, success messages
- **Mobile Forms**: Touch-friendly inputs, proper keyboard handling
- **Security**: Password field handling, credential masking

## Running Tests

### Automatic Backend Setup
The e2e tests now automatically manage the backend services. When you run tests locally, they will:
1. Check if Docker services are already running
2. Start services if needed (postgres, redis, backend, frontend)
3. Wait for all services to be healthy
4. Run the tests
5. Stop services after tests complete (unless configured otherwise)

### Quick Start
```bash
# From the frontend directory
npm run test:e2e
```

### Manual Service Management
If you prefer to manage services manually:

```bash
# Start services
just test-services-up

# Run tests (skip automatic setup)
SKIP_DOCKER_SETUP=1 npm run test:e2e

# Stop services when done
just test-down
```

### Keep Services Running
To keep services running after tests (useful for debugging):

```bash
KEEP_SERVICES_RUNNING=1 npm run test:e2e
```

### Using the Test Script
A convenience script is provided:

```bash
# Run tests with automatic setup
./tests/e2e/local-test.sh

# Keep services running after tests
./tests/e2e/local-test.sh --keep-running

# Skip Docker setup (assumes services are running)
./tests/e2e/local-test.sh --skip-setup
```

### Run specific browser
```bash
npm run test:e2e -- --project=chromium
npm run test:e2e -- --project=firefox
npm run test:e2e -- --project=webkit
npm run test:e2e -- --project=mobile-safari-iphone
npm run test:e2e -- --project=mobile-safari-ipad
```

### Run specific test file
```bash
npm run test:e2e -- tests/e2e/auth.spec.ts
```

### Run with UI mode (interactive)
```bash
npm run test:e2e:ui
```

### Debug a specific test
```bash
npm run test:e2e -- --debug tests/e2e/auth.spec.ts
```

## Test Environment

Tests run against a local development environment by default:
- Frontend: http://localhost:3000
- Backend: http://localhost:8000

The Playwright configuration automatically starts the frontend dev server.

## CI/CD Integration

The GitHub Actions workflow (`e2e-tests.yml`) runs tests:
- On all supported browsers (Chromium, Firefox, Safari)
- On mobile viewports (iPhone, iPad)
- In headless mode for CI environments
- With test artifacts (reports, videos) uploaded on failure

## Writing New Tests

### Test Structure
```typescript
test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    // Common setup
  });

  test('should do something', async ({ page }) => {
    // Arrange
    await page.goto('/path');

    // Act
    await page.click('button');

    // Assert
    await expect(page.locator('element')).toBeVisible();
  });
});
```

### Best Practices
1. Use semantic selectors (roles, labels, text)
2. Add proper test descriptions
3. Mock API responses for deterministic tests
4. Test both success and error scenarios
5. Include mobile-specific tests
6. Add accessibility checks

### Common Helpers
- `setupAuthentication()`: Mock authenticated state
- `generateTestUser()`: Create unique test data
- `fillLoginForm()`: Fill login form fields
- `fillRegistrationForm()`: Fill registration form fields

## Debugging Failed Tests

1. **Check test report**: `npx playwright show-report`
2. **View trace**: Tests save traces on failure
3. **Screenshots**: Available in `test-results/` directory
4. **Videos**: Recorded for failed tests
5. **Run headed**: Remove headless mode to see browser
