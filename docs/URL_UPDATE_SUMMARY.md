# URL Update Summary

## Overview
Updated all VinylDigger GitHub repository URL references to use the correct repository: `https://github.com/SimplicityGuy/vinyldigger`

## Files Updated

### 1. Backend Service Configuration
- **File**: `backend/src/services/discogs.py`
- **Change**: Updated User-Agent header from `yourusername/vinyldigger` to `SimplicityGuy/vinyldigger`
- **Purpose**: Ensures Discogs API requests have the correct contact URL

### 2. Documentation
- **File**: `docs/deployment.md`
- **Change**: Updated git clone URL
- **Purpose**: Users will clone from the correct repository

- **File**: `docs/troubleshooting.md`
- **Change**: Updated GitHub Issues link
- **Purpose**: Users will be directed to the correct issues page

- **File**: `CONTRIBUTING.md`
- **Change**: Updated git clone URL
- **Purpose**: Contributors will clone from the correct repository

### 3. Docker Container Labels
- **Files**:
  - `backend/Dockerfile`
  - `frontend/Dockerfile`
- **Changes**: Updated OCI image labels for source and documentation URLs
- **Purpose**: Container metadata points to the correct repository

## URLs Not Changed
- Example domain URLs (e.g., `https://vinyldigger.com`) - These are placeholder examples
- README.md - Already had the correct URL
- Service names and internal references - These don't need updating

## Verification
To verify all URLs are correct, run:
```bash
grep -r "github.com.*vinyldigger" . --exclude-dir=.git --exclude="*.md"
```

This should only show references to `SimplicityGuy/vinyldigger`.
