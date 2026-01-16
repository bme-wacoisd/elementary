# Bluebonnet Learning Canvas Spider

## Overview

This document describes the process for downloading all curriculum files from the Bluebonnet Learning courses hosted on Canvas LMS at `tealearn.instructure.com`.

## Target Courses

| Course ID | Expected Content |
|-----------|------------------|
| 9564 | Bluebonnet Learning (likely Grade K FS) |
| 9565 | Bluebonnet Learning course |
| 9534 | Bluebonnet Learning course |
| 9575 | Bluebonnet Learning course |
| 9548 | Bluebonnet Learning course |
| 9549 | Bluebonnet Learning course |
| 9554 | Bluebonnet Learning course |
| 9555 | Bluebonnet Learning course |
| 9532 | Bluebonnet Learning course |
| 9556 | Bluebonnet Learning course |
| 9533 | Bluebonnet Learning course |
| 9539 | Bluebonnet Learning course |
| 9540 | Bluebonnet Learning course |
| 9541 | Bluebonnet Learning course |
| 9542 | Bluebonnet Learning course |
| 9543 | Bluebonnet Learning course |
| 9535 | Bluebonnet Learning course |
| 9544 | Bluebonnet Learning course |
| 9545 | Bluebonnet Learning course |
| 9546 | Bluebonnet Learning course |

**Total: 20 courses**

## Canvas API Endpoints

### Authentication
Canvas LMS requires authentication. Options:
1. **Session Cookie**: If logged in via browser, session cookies work for API calls
2. **API Token**: Generate from Canvas Settings > Access Tokens

### Endpoints Used

```
Base URL: https://tealearn.instructure.com

GET /api/v1/courses/{course_id}
    Returns: Course name, code, enrollment info

GET /api/v1/courses/{course_id}/folders?per_page=100
    Returns: All folders with hierarchy information
    Pagination: Link header with rel="next"

GET /api/v1/courses/{course_id}/files?per_page=100
    Returns: All files with download URLs
    Pagination: Link header with rel="next"

GET /files/{file_id}/download?download_frd=1
    Returns: File binary (follows redirect to S3/CDN)
```

## Implementation Approach

### Phase 1: Discovery (Manifest Generation)

First, catalog all available content without downloading:

1. Query each course for basic info
2. Enumerate all folders to understand structure
3. List all files with sizes and types
4. Save manifest.json for reference

### Phase 2: Download

With manifest in hand:

1. Create local directory structure mirroring Canvas folders
2. Download files respecting rate limits (500ms between requests)
3. Skip files that already exist with matching size
4. Log progress and errors

### Rate Limiting Strategy

To be a good citizen:
- **500ms** minimum delay between API calls
- **Exponential backoff** on errors (1s, 2s, 4s)
- **Max 3 retries** per request before logging failure
- **Sequential processing** of courses (not parallel)

## File Organization

### Canvas Structure
```
Course
└── Folders (hierarchical)
    └── Files
```

### Local Structure
```
canvas_downloads/
└── {Course Name}/
    └── {Folder Path}/
        └── {File Name}
```

### Name Sanitization

Characters removed/replaced for filesystem compatibility:
- `< > : " / \ | ? *` → `_`
- Whitespace normalized
- Length limited to 200 characters

## Expected Output

Based on initial analysis:
- **~20 courses** covering K-5 curriculum
- **Thousands of files** per course
- **Estimated total size**: 50-100 GB
- **File types**: Primarily PDF, with DOCX, PPTX, media files

## Running the Spider

### Prerequisites

- Node.js 18+ with TypeScript support
- Network access to tealearn.instructure.com
- Authentication credentials (cookie or API token)
- Sufficient disk space (plan for 100GB+)

### Commands

```bash
# Step 1: Generate manifest only (recommended first)
npx ts-node canvas_file_downloader.ts --manifest-only

# Step 2: Review manifest.json to understand scope

# Step 3: Full download
npx ts-node canvas_file_downloader.ts

# Alternative: Use curl-based shell script
./canvas_downloader.sh
```

### Monitoring Progress

The script outputs:
- Course name as it starts each one
- Folder and file counts discovered
- Each file as it downloads (with size)
- Summary statistics at completion

### Resuming Interrupted Downloads

The script checks existing files before downloading:
- If file exists with matching size → skipped
- If file exists with different size → re-downloaded
- If file doesn't exist → downloaded

This makes it safe to restart after interruption.

## Troubleshooting

### 401 Unauthorized
- Session expired; refresh authentication
- API token invalid or missing required scopes

### 403 Forbidden
- Course access not granted to your account
- File-level permissions restricted

### 429 Too Many Requests
- Increase RATE_LIMIT_MS value
- Wait before retrying

### Incomplete Downloads
- Check network stability
- Review error log for specific failures
- Re-run script (will skip completed files)

## Post-Download Verification

```bash
# Verify file counts match manifest
cat manifest.json | jq '.courses[].total_files' | awk '{s+=$1} END {print s}'
find canvas_downloads -type f | wc -l

# Check for zero-byte files (failed downloads)
find canvas_downloads -type f -size 0

# Verify PDF integrity
find canvas_downloads -name "*.pdf" -exec pdfinfo {} \; 2>&1 | grep -i error
```

## Security Notes

- Do not commit authentication tokens to version control
- Downloaded materials are copyrighted; respect usage terms
- Store credentials in environment variables or secure files

## Maintenance

If the Canvas course content is updated:
1. Re-run the manifest generation to see changes
2. Run full download; only new/changed files will download
3. Consider archiving previous versions if needed
