#!/bin/bash
# Script to run e2e tests locally with proper setup

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}VinylDigger E2E Test Runner${NC}"
echo "=============================="

# Parse command line arguments
KEEP_RUNNING=false
SKIP_SETUP=false
while [[ $# -gt 0 ]]; do
  case $1 in
    --keep-running)
      KEEP_RUNNING=true
      shift
      ;;
    --skip-setup)
      SKIP_SETUP=true
      shift
      ;;
    --help)
      echo "Usage: ./local-test.sh [options]"
      echo ""
      echo "Options:"
      echo "  --keep-running    Keep services running after tests"
      echo "  --skip-setup      Skip docker setup (assumes services are running)"
      echo "  --help           Show this help message"
      exit 0
      ;;
    *)
      shift
      ;;
  esac
done

# Export environment variables
if [ "$KEEP_RUNNING" = true ]; then
  export KEEP_SERVICES_RUNNING=1
fi

if [ "$SKIP_SETUP" = true ]; then
  export SKIP_DOCKER_SETUP=1
fi

# Check if we're in the frontend directory
if [ ! -f "package.json" ] || [ ! -d "tests/e2e" ]; then
  echo -e "${RED}Error: This script must be run from the frontend directory${NC}"
  exit 1
fi

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
  echo -e "${YELLOW}Installing frontend dependencies...${NC}"
  npm ci
fi

# Install Playwright browsers if needed
if [ ! -d "$HOME/.cache/ms-playwright" ]; then
  echo -e "${YELLOW}Installing Playwright browsers...${NC}"
  npx playwright install --with-deps chromium
fi

# Run the tests
echo -e "${GREEN}Running E2E tests...${NC}"
npm run test:e2e

# Check exit code
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
  echo -e "${GREEN}✓ All tests passed!${NC}"
else
  echo -e "${RED}✗ Some tests failed${NC}"
  echo -e "${YELLOW}View the test report with: npx playwright show-report${NC}"
fi

# Show helpful message about services
if [ "$KEEP_RUNNING" = true ] && [ "$SKIP_SETUP" != true ]; then
  echo -e "${YELLOW}Services are still running. To stop them, run:${NC}"
  echo "cd .. && docker-compose -f docker-compose.test.yml down -v"
fi

exit $EXIT_CODE
