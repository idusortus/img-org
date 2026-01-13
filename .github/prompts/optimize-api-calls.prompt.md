---
name: Optimize API Calls
description: Review code for Google Drive API efficiency and suggest optimizations for pagination, batching, and rate limiting
tags: [google-drive, performance, api, optimization]
---

# Optimize API Calls

You are reviewing code that interacts with the Google Drive API v3 to ensure it's efficient and won't hit rate limits.

## What to Check

### 1. Pagination
- ✅ **Must have**: Loop with `nextPageToken`
- ✅ **Must have**: Handle `pageSize` parameter (max 100)
- ❌ **Never**: Assume all results in one request

```python
# Bad
files = service.files().list(q=query).execute().get('files', [])

# Good
all_files = []
page_token = None
while True:
    results = service.files().list(
        q=query,
        pageToken=page_token,
        pageSize=100
    ).execute()
    all_files.extend(results.get('files', []))
    page_token = results.get('nextPageToken')
    if not page_token:
        break
```

### 2. Field Selection
- ✅ **Must have**: Specify only needed fields
- ❌ **Never**: Request all fields with default call

```python
# Bad - returns everything
files = service.files().list().execute()

# Good - only what's needed
files = service.files().list(
    fields='nextPageToken, files(id, name, md5Checksum, size)'
).execute()
```

### 3. Rate Limiting
- ✅ **Must have**: Exponential backoff for 429 errors
- ✅ **Must have**: Retry logic for 500-503 errors
- ✅ **Should have**: Request counting/monitoring

```python
# Required pattern
import time
from googleapiclient.errors import HttpError

def execute_with_retry(request, max_retries=5):
    for attempt in range(max_retries):
        try:
            return request.execute()
        except HttpError as e:
            if e.resp.status in [429, 500, 503]:
                wait_time = 2 ** attempt
                time.sleep(wait_time)
                if attempt == max_retries - 1:
                    raise
            else:
                raise
```

### 4. Batch Requests
- ✅ **Should use**: Batch requests for multiple operations
- ✅ **Should use**: Batch size of 100 (API limit)

```python
# Bad - multiple individual requests
for file_id in file_ids:
    service.files().get(fileId=file_id).execute()

# Good - single batch request
batch = service.new_batch_http_request()
for file_id in file_ids[:100]:  # Max 100 per batch
    batch.add(service.files().get(fileId=file_id))
batch.execute()
```

### 5. Thumbnail Usage
- ✅ **Should use**: Download thumbnails for previews
- ❌ **Avoid**: Downloading full images just for display

```python
# Bad - downloads full 5MB image for preview
request = service.files().get_media(fileId=file_id)

# Good - use thumbnail link
metadata = service.files().get(
    fileId=file_id, 
    fields='thumbnailLink'
).execute()
```

### 6. Caching
- ✅ **Should have**: Cache file metadata locally
- ✅ **Should have**: Avoid redundant API calls
- ✅ **Should have**: Store tokens/credentials properly

## Quota Awareness

Google Drive API default quotas:
- 10,000 requests/day
- 1,000 requests/100 seconds/user

Check if code:
- Monitors request count
- Warns user of approaching limits
- Implements request throttling

## Your Response

For each issue found, provide:
1. **Location**: Line number or code snippet
2. **Issue**: What's inefficient
3. **Impact**: Rate limit risk, slow performance, wasted bandwidth
4. **Fix**: Corrected code
5. **Improvement**: Estimated performance gain

## Example Output

```
Issue #1: Missing Pagination
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Location: line 45
Current code:
    files = service.files().list(q=query).execute()

Problem:
- Only retrieves first 100 files
- Will miss files if >100 exist
- User will get incomplete results

Fix:
    all_files = []
    page_token = None
    while True:
        results = service.files().list(
            q=query,
            pageToken=page_token,
            pageSize=100
        ).execute()
        all_files.extend(results.get('files', []))
        page_token = results.get('nextPageToken')
        if not page_token:
            break

Impact: CRITICAL - Missing data
Improvement: Handles unlimited files
```

## Focus Areas

Prioritize checking for:
1. Missing pagination (critical)
2. No rate limit handling (critical)  
3. Requesting all fields (high impact)
4. Individual requests instead of batching (high impact)
5. Downloading full images unnecessarily (medium impact)
6. Missing error handling (medium impact)

## Additional Optimizations

Suggest:
- Parallel processing where safe
- Progress indicators for long operations
- Local caching strategies
- Query optimization tips
