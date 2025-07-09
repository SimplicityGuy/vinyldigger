# Fix: `just: command not found` in GitHub Actions

## Problem

The error `just: command not found` occurs when GitHub Actions tries to run `just` commands but the tool isn't installed. This particularly happens:

1. On macOS runners (the arkade installation method only works reliably on Linux)
2. In cleanup steps that run with `if: always()` even after job failures
3. When installation steps fail silently

## Root Cause

The original workflows used `arkade-get` to install `just`, which:
- Works inconsistently across different OS platforms
- Doesn't provide clear error messages on installation failure
- Isn't the recommended installation method for `just`

## Solution

### 1. Switch to Official `just` Installation Action

Replaced arkade-get with the official `extractions/setup-just` action:

```yaml
- name: Install just
  uses: extractions/setup-just@dd310ad5a97d8e7b41793f8ef055398d51ad4de6 # v2.0.0
  with:
    just-version: '1.38.0'  # Pin to specific version for reliability
```

Benefits:
- Works reliably on all platforms (Linux, macOS, Windows)
- Faster installation
- Clear error messages if installation fails
- Version pinning for reproducibility

### 2. Platform-Specific docker-compose Installation

Added platform check for docker-compose since macOS has it built-in:

```yaml
- name: Install docker-compose
  if: runner.os == 'Linux'  # macOS has docker-compose built-in
  uses: alexellis/arkade-get@1eef818e467c387d3f50cfe0d2c565d1cbe82b03
  with:
    docker-compose: latest
```

### 3. Graceful Fallback in Cleanup Steps

Added fallback logic for cleanup steps that run with `if: always()`:

```yaml
- name: Stop services
  if: always()
  run: |
    # Ensure just is available or use fallback
    if command -v just &> /dev/null; then
      just test-down
    else
      echo "Warning: 'just' not found, using docker-compose directly"
      docker-compose -f docker-compose.test.yml down -v || docker compose -f docker-compose.test.yml down -v || true
    fi
```

### 4. Created Reusable Action

Created `.github/actions/setup-tools/action.yml` for consistent tool installation across workflows.

## Changes Made

1. **`.github/workflows/ci.yml`**:
   - Replaced arkade-get with setup-just for all jobs
   - Added platform check for docker-compose

2. **`.github/workflows/e2e-tests.yml`**:
   - Replaced arkade-get with setup-just
   - Added fallback logic in cleanup step
   - Added platform check for docker-compose

3. **`.github/actions/setup-tools/action.yml`** (new):
   - Reusable action for tool installation
   - Configurable options for each tool
   - Verification step to confirm installations

## Prevention

1. **Always use official installation methods** for tools when available
2. **Test workflows on all target platforms** (use matrix strategy)
3. **Add verification steps** after tool installation
4. **Use fallback commands** in cleanup steps
5. **Pin tool versions** for reproducibility

## Testing the Fix

To verify the fix works:

```bash
# Test locally with act (GitHub Actions emulator)
act -j test

# Or push to a branch and check Actions tab
git checkout -b test-just-fix
git add .
git commit -m "fix: ensure just is always available in CI"
git push origin test-just-fix
```

## Related Issues

- Missing tools in CI environments
- Platform-specific installation differences
- Silent installation failures
- Cleanup steps failing after job errors

---

*This fix ensures `just` is always available across all platforms and provides graceful fallbacks when needed.*
