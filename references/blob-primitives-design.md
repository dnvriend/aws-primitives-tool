# Blob Primitives Design Document

**Author:** Dennis Vriend
**Date:** 2025-11-15
**Status:** Design Document
**Version:** 1.0

> Design specification for S3-backed blob storage primitives for artifacts, datasets, checkpoints, and distributed file operations.

---

## Table of Contents

1. [Overview](#overview)
2. [Design Principles](#design-principles)
3. [S3 Architecture](#s3-architecture)
4. [Primitive Operations](#primitive-operations)
5. [CLI Command Specifications](#cli-command-specifications)
6. [Implementation Architecture](#implementation-architecture)
7. [Error Handling](#error-handling)
8. [Use Cases & Examples](#use-cases--examples)
9. [Cost Analysis](#cost-analysis)
10. [Testing Strategy](#testing-strategy)

---

## Overview

The `blob` primitive provides scalable, durable object storage backed by Amazon S3. It enables distributed file operations including:

- **File Upload/Download** - Single file and batch operations
- **Directory Sync** - Bidirectional synchronization
- **Streaming** - Efficient large file handling
- **Multipart Uploads** - Parallel chunk uploads for speed
- **Presigned URLs** - Temporary access without credentials
- **Lifecycle Management** - Automatic archival and expiration
- **Event Triggers** - S3 events → EventBridge → Lambda workflows
- **Versioning** - Immutable artifact history
- **Metadata** - Custom key-value tags

### Why S3?

✅ **Unlimited Scale** - Store petabytes without provisioning
✅ **11-Nines Durability** - 99.999999999% data durability
✅ **Cost-Effective** - $0.023/GB-month (EU), cheaper than EBS/EFS
✅ **Event-Driven** - Native EventBridge integration
✅ **Versioning** - Immutable history, rollback capability
✅ **Lifecycle Rules** - Auto-archive to Glacier, auto-delete old files
✅ **Global Accessibility** - Access from anywhere with credentials

---

## Design Principles

### 1. S3-Native Operations

**Use S3 features, not workarounds:**

- Use S3 multipart uploads for files >100MB (5GB max per part, up to 10,000 parts = 50TB files)
- Use S3 Select for querying data without downloading
- Use S3 presigned URLs for temporary access
- Use S3 lifecycle rules for automatic archival
- Use S3 event notifications for triggers

### 2. CLI-Friendly & Pipeable

**Commands must compose with shell tools:**

```bash
# Pipe to S3
cat large-file.csv | blob put - s3://bucket/data.csv

# Pipe from S3
blob get s3://bucket/data.csv - | jq '.records[]'

# Generate and upload
generate-report.sh | blob put - s3://bucket/reports/$(date +%Y-%m-%d).html

# Download and process
blob get s3://bucket/logs/app.log - | grep ERROR
```

### 3. Transparent Multipart Uploads

**Automatic chunking for large files:**

- Files <100MB: Single PUT operation
- Files ≥100MB: Automatic multipart upload (parallel chunks)
- Configurable chunk size (default: 100MB, max: 5GB)
- Automatic retry on chunk failure
- Progress reporting for large transfers

### 4. S3 URI Conventions

**Consistent path handling:**

```bash
# S3 URIs
s3://bucket/key
s3://bucket/path/to/file.txt

# Local paths
./local-file.txt
/absolute/path/file.txt
- (stdin/stdout)

# Support for prefixes
s3://bucket/prefix/  # Trailing slash indicates prefix
```

### 5. Idempotent Operations

**Same command, same effect:**

- `put` with same content → No-op if unchanged (ETag match)
- `delete` non-existent key → Success (idempotent)
- `sync` → Only transfer changed files (checksum comparison)
- `copy` with `--if-not-exists` → Skip if destination exists

---

## S3 Architecture

### Bucket Organization

**Recommended structure for Claude Code workflows:**

```
claude-code-artifacts/
├── sessions/                      # Session history (JSONL)
│   ├── 2025-11-15/
│   │   ├── session-123.jsonl
│   │   └── session-456.jsonl
│   └── 2025-11-16/
├── checkpoints/                   # Agent state snapshots
│   ├── agent-abc/
│   │   ├── checkpoint-001.json
│   │   └── checkpoint-002.json
│   └── agent-xyz/
├── datasets/                      # Shared datasets
│   ├── training/
│   │   ├── data-001.parquet
│   │   └── data-002.parquet
│   └── inference/
├── artifacts/                     # Build artifacts
│   ├── v1.0.0/
│   │   ├── app.zip
│   │   └── app.tar.gz
│   └── v1.0.1/
├── logs/                          # Application logs
│   ├── 2025-11-15/
│   │   ├── app.log
│   │   └── error.log
│   └── 2025-11-16/
└── reports/                       # Generated reports
    ├── daily/
    └── weekly/
```

### S3 Features Configuration

**Bucket settings:**

```json
{
  "Bucket": "claude-code-artifacts",
  "Region": "eu-central-1",
  "Versioning": "Enabled",
  "LifecycleRules": [
    {
      "Id": "archive-old-sessions",
      "Status": "Enabled",
      "Prefix": "sessions/",
      "Transitions": [
        {"Days": 30, "StorageClass": "STANDARD_IA"},
        {"Days": 90, "StorageClass": "GLACIER"}
      ]
    },
    {
      "Id": "delete-old-logs",
      "Status": "Enabled",
      "Prefix": "logs/",
      "Expiration": {"Days": 90}
    }
  ],
  "EventBridgeConfiguration": {
    "EventBridgeEnabled": true
  },
  "Tags": [
    {"Key": "Project", "Value": "claude-code"},
    {"Key": "Environment", "Value": "production"}
  ]
}
```

### Storage Classes

**Choose right class for workload:**

| Storage Class | Use Case | Cost (EU) | Retrieval |
|--------------|----------|-----------|-----------|
| **STANDARD** | Frequent access | $0.023/GB-month | Free, instant |
| **STANDARD_IA** | Infrequent access (30+ days) | $0.0125/GB-month | $0.01/GB |
| **GLACIER** | Archive (90+ days) | $0.0040/GB-month | Hours ($0.033/GB) |
| **GLACIER_DEEP_ARCHIVE** | Long-term archive (180+ days) | $0.00099/GB-month | 12+ hours ($0.02/GB) |
| **INTELLIGENT_TIERING** | Unpredictable access | $0.023/GB-month + $0.0025/1k objects | Auto-optimized |

**Recommendation:**
- Hot data (sessions, checkpoints): **STANDARD**
- Warm data (old artifacts): **STANDARD_IA** (auto-transition after 30 days)
- Cold data (archives): **GLACIER** (auto-transition after 90 days)

---

## Primitive Operations

### 1. Upload Operations

#### `put` - Upload file or stdin

**Operation:** `PutObject` (single) or `CreateMultipartUpload` (large files)

```bash
blob put <local-path> <s3-uri> [OPTIONS]

# Examples
blob put ./build/app.zip s3://artifacts/v1.0.0/app.zip
blob put - s3://logs/$(date +%Y-%m-%d).log < app.log
cat report.json | blob put - s3://reports/daily/$(date +%s).json

# Options
--metadata KEY=VALUE       # Custom metadata (multiple allowed)
--tags KEY=VALUE           # Tags (multiple allowed)
--content-type TYPE        # MIME type (auto-detected if omitted)
--storage-class CLASS      # STANDARD, STANDARD_IA, GLACIER, etc.
--if-not-exists            # Skip if object exists (idempotent)
--if-match ETAG            # Upload only if ETag matches (optimistic locking)
--chunk-size SIZE          # Multipart chunk size (default: 100MB)
--progress                 # Show progress bar
```

**Boto3 Implementation (Single PUT):**
```python
s3.put_object(
    Bucket='artifacts',
    Key='v1.0.0/app.zip',
    Body=file_content,
    ContentType='application/zip',
    Metadata={'version': '1.0.0', 'build': '123'},
    Tags='project=claude-code&env=prod',
    StorageClass='STANDARD'
)
```

**Boto3 Implementation (Multipart):**
```python
# Step 1: Initiate multipart upload
response = s3.create_multipart_upload(
    Bucket='artifacts',
    Key='v1.0.0/large-file.zip'
)
upload_id = response['UploadId']

# Step 2: Upload parts in parallel (100MB chunks)
parts = []
for i, chunk in enumerate(read_chunks(file, chunk_size=100*1024*1024), start=1):
    part = s3.upload_part(
        Bucket='artifacts',
        Key='v1.0.0/large-file.zip',
        PartNumber=i,
        UploadId=upload_id,
        Body=chunk
    )
    parts.append({'PartNumber': i, 'ETag': part['ETag']})

# Step 3: Complete multipart upload
s3.complete_multipart_upload(
    Bucket='artifacts',
    Key='v1.0.0/large-file.zip',
    UploadId=upload_id,
    MultipartUpload={'Parts': parts}
)
```

**Output (JSON):**
```json
{
  "bucket": "artifacts",
  "key": "v1.0.0/app.zip",
  "size": 12345678,
  "etag": "d41d8cd98f00b204e9800998ecf8427e",
  "version_id": "abc123",
  "storage_class": "STANDARD",
  "uploaded_at": 1731696000
}
```

---

#### `put-dir` - Upload directory recursively

**Operation:** Parallel `PutObject` for multiple files

```bash
blob put-dir <local-dir> <s3-prefix> [OPTIONS]

# Examples
blob put-dir ./build/ s3://artifacts/v1.0.0/
blob put-dir ./src/ s3://backup/src/ --exclude "*.pyc" --exclude "__pycache__"

# Options
--exclude PATTERN          # Exclude files matching pattern (glob)
--include PATTERN          # Include only files matching pattern
--parallel N               # Number of parallel uploads (default: 10)
--delete                   # Delete S3 objects not in local dir (sync mode)
--dry-run                  # Show what would be uploaded
--progress                 # Show progress
```

**Implementation Strategy:**
```python
# 1. Walk local directory
files_to_upload = []
for root, dirs, files in os.walk(local_dir):
    for file in files:
        if not should_exclude(file, exclude_patterns):
            local_path = os.path.join(root, file)
            relative_path = os.path.relpath(local_path, local_dir)
            s3_key = f"{s3_prefix}/{relative_path}"
            files_to_upload.append((local_path, s3_key))

# 2. Upload in parallel using ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=parallel) as executor:
    futures = []
    for local_path, s3_key in files_to_upload:
        future = executor.submit(upload_file, local_path, s3_key)
        futures.append(future)

    # Wait for all uploads with progress tracking
    for future in as_completed(futures):
        result = future.result()  # Raises exception if upload failed
        print(f"Uploaded: {result['key']}")
```

---

### 2. Download Operations

#### `get` - Download file or to stdout

**Operation:** `GetObject`

```bash
blob get <s3-uri> <local-path> [OPTIONS]

# Examples
blob get s3://artifacts/v1.0.0/app.zip ./app.zip
blob get s3://logs/app.log - | grep ERROR
blob get s3://reports/daily/report.json - | jq '.summary'

# Options
--version-id ID            # Download specific version
--range BYTES              # Download byte range (e.g., "0-1023" for first KB)
--if-match ETAG            # Download only if ETag matches
--if-modified-since DATE   # Download only if modified after date
--progress                 # Show progress bar
```

**Boto3 Implementation:**
```python
response = s3.get_object(
    Bucket='artifacts',
    Key='v1.0.0/app.zip',
    VersionId='abc123',  # Optional
    Range='bytes=0-1048576'  # Optional: first 1MB
)

# Stream to file or stdout
with open(local_path, 'wb') as f:
    for chunk in response['Body'].iter_chunks(chunk_size=8192):
        f.write(chunk)
```

**Output (JSON):**
```json
{
  "bucket": "artifacts",
  "key": "v1.0.0/app.zip",
  "size": 12345678,
  "etag": "d41d8cd98f00b204e9800998ecf8427e",
  "version_id": "abc123",
  "content_type": "application/zip",
  "last_modified": 1731696000,
  "metadata": {
    "version": "1.0.0",
    "build": "123"
  }
}
```

---

#### `get-dir` - Download directory recursively

**Operation:** Parallel `GetObject` for multiple files

```bash
blob get-dir <s3-prefix> <local-dir> [OPTIONS]

# Examples
blob get-dir s3://artifacts/v1.0.0/ ./downloaded/
blob get-dir s3://backup/src/ ./restored-src/ --exclude "*.log"

# Options
--exclude PATTERN          # Exclude files matching pattern
--include PATTERN          # Include only files matching pattern
--parallel N               # Number of parallel downloads (default: 10)
--delete                   # Delete local files not in S3 (sync mode)
--dry-run                  # Show what would be downloaded
--progress                 # Show progress
```

---

### 3. List Operations

#### `list` - List objects by prefix

**Operation:** `ListObjectsV2`

```bash
blob list <s3-prefix> [OPTIONS]

# Examples
blob list s3://artifacts/
blob list s3://artifacts/v1.0.0/ --recursive
blob list s3://logs/ --format keys
blob list s3://artifacts/ --since "2025-11-01" --before "2025-11-15"

# Options
--recursive / -r           # List all objects recursively
--format json|keys|table   # Output format (default: json)
--limit N                  # Max objects to return
--since DATE               # Filter by last modified after date
--before DATE              # Filter by last modified before date
--min-size SIZE            # Filter by minimum size (e.g., "1MB")
--max-size SIZE            # Filter by maximum size
```

**Boto3 Implementation:**
```python
paginator = s3.get_paginator('list_objects_v2')
pages = paginator.paginate(
    Bucket='artifacts',
    Prefix='v1.0.0/',
    MaxKeys=1000
)

objects = []
for page in pages:
    for obj in page.get('Contents', []):
        if matches_filters(obj, since, before, min_size, max_size):
            objects.append({
                'key': obj['Key'],
                'size': obj['Size'],
                'last_modified': obj['LastModified'].isoformat(),
                'etag': obj['ETag'],
                'storage_class': obj.get('StorageClass', 'STANDARD')
            })
```

**Output (JSON):**
```json
{
  "bucket": "artifacts",
  "prefix": "v1.0.0/",
  "objects": [
    {
      "key": "v1.0.0/app.zip",
      "size": 12345678,
      "last_modified": "2025-11-15T10:30:00Z",
      "etag": "d41d8cd98f00b204e9800998ecf8427e",
      "storage_class": "STANDARD"
    }
  ],
  "total_count": 1,
  "total_size": 12345678
}
```

---

### 4. Delete Operations

#### `delete` - Delete object(s)

**Operation:** `DeleteObject` or `DeleteObjects` (batch)

```bash
blob delete <s3-uri> [OPTIONS]

# Examples
blob delete s3://artifacts/v1.0.0/app.zip
blob delete s3://logs/ --recursive --older-than 90d
blob delete s3://temp/ --recursive --dry-run

# Options
--recursive / -r           # Delete all objects with prefix
--older-than DURATION      # Delete objects older than duration (e.g., "30d", "24h")
--dry-run / -n             # Show what would be deleted
--force / -f               # Skip confirmation prompt
--version-id ID            # Delete specific version
```

**Boto3 Implementation (Single):**
```python
s3.delete_object(
    Bucket='artifacts',
    Key='v1.0.0/app.zip',
    VersionId='abc123'  # Optional
)
```

**Boto3 Implementation (Batch):**
```python
# Delete up to 1000 objects per request
objects_to_delete = [{'Key': key} for key in keys_to_delete]

response = s3.delete_objects(
    Bucket='artifacts',
    Delete={'Objects': objects_to_delete}
)

# Check for errors
deleted = response.get('Deleted', [])
errors = response.get('Errors', [])
```

---

### 5. Copy Operations

#### `copy` - Copy object within S3

**Operation:** `CopyObject` (single) or `CreateMultipartUpload` + `UploadPartCopy` (large)

```bash
blob copy <source-s3-uri> <dest-s3-uri> [OPTIONS]

# Examples
blob copy s3://artifacts/v1.0.0/app.zip s3://backup/v1.0.0/app.zip
blob copy s3://bucket-a/file.txt s3://bucket-b/file.txt --if-not-exists
blob copy s3://artifacts/latest.zip s3://artifacts/v1.0.0.zip --metadata version=1.0.0

# Options
--if-not-exists            # Skip if destination exists
--metadata KEY=VALUE       # Override metadata (multiple allowed)
--storage-class CLASS      # Destination storage class
--metadata-directive COPY|REPLACE  # Copy or replace metadata
```

**Boto3 Implementation:**
```python
s3.copy_object(
    CopySource={'Bucket': 'artifacts', 'Key': 'v1.0.0/app.zip'},
    Bucket='backup',
    Key='v1.0.0/app.zip',
    MetadataDirective='COPY',  # or 'REPLACE'
    StorageClass='STANDARD_IA'
)
```

---

### 6. Sync Operations

#### `sync` - Bidirectional synchronization

**Operation:** `ListObjectsV2` + conditional `PutObject`/`GetObject`/`DeleteObject`

```bash
blob sync <source> <destination> [OPTIONS]

# Examples (Local → S3)
blob sync ./build/ s3://artifacts/latest/

# Examples (S3 → Local)
blob sync s3://artifacts/latest/ ./downloaded/

# Examples (S3 → S3)
blob sync s3://bucket-a/data/ s3://bucket-b/backup/

# Options
--delete                   # Delete dest files not in source
--exclude PATTERN          # Exclude files matching pattern
--include PATTERN          # Include only files matching pattern
--size-only                # Compare by size only (skip checksum)
--checksum                 # Use MD5 checksum for comparison (default)
--dry-run / -n             # Show what would be synced
--parallel N               # Parallel transfers (default: 10)
```

**Sync Algorithm:**
```python
def sync(source, destination):
    # 1. List source and destination
    source_files = list_files(source)
    dest_files = list_files(destination)

    # 2. Determine operations
    to_upload = []
    to_delete = []

    for file in source_files:
        dest_file = dest_files.get(file.key)
        if not dest_file:
            to_upload.append(file)  # New file
        elif file.etag != dest_file.etag:
            to_upload.append(file)  # Changed file
        # else: No change, skip

    if delete_flag:
        for file in dest_files:
            if file.key not in source_files:
                to_delete.append(file)  # Removed from source

    # 3. Execute operations in parallel
    with ThreadPoolExecutor(max_workers=parallel) as executor:
        upload_futures = [executor.submit(upload, f) for f in to_upload]
        delete_futures = [executor.submit(delete, f) for f in to_delete]
        wait(upload_futures + delete_futures)
```

---

### 7. Metadata Operations

#### `head` - Get object metadata

**Operation:** `HeadObject`

```bash
blob head <s3-uri> [OPTIONS]

# Examples
blob head s3://artifacts/v1.0.0/app.zip
blob head s3://artifacts/v1.0.0/app.zip --version-id abc123

# Options
--version-id ID            # Check specific version
```

**Output (JSON):**
```json
{
  "bucket": "artifacts",
  "key": "v1.0.0/app.zip",
  "size": 12345678,
  "etag": "d41d8cd98f00b204e9800998ecf8427e",
  "version_id": "abc123",
  "content_type": "application/zip",
  "last_modified": "2025-11-15T10:30:00Z",
  "storage_class": "STANDARD",
  "metadata": {
    "version": "1.0.0",
    "build": "123"
  },
  "tags": {
    "project": "claude-code",
    "env": "prod"
  }
}
```

---

#### `tag` - Add/update tags

**Operation:** `PutObjectTagging`

```bash
blob tag <s3-uri> <KEY=VALUE> [KEY=VALUE...] [OPTIONS]

# Examples
blob tag s3://artifacts/v1.0.0/app.zip env=prod version=1.0.0
blob tag s3://artifacts/v1.0.0/app.zip env=prod --version-id abc123

# Options
--version-id ID            # Tag specific version
```

---

#### `untag` - Remove tags

**Operation:** `DeleteObjectTagging`

```bash
blob untag <s3-uri> [OPTIONS]

# Examples
blob untag s3://artifacts/v1.0.0/app.zip
```

---

### 8. Presigned URL Operations

#### `presign` - Generate temporary access URL

**Operation:** `generate_presigned_url`

```bash
blob presign <s3-uri> [OPTIONS]

# Examples
blob presign s3://artifacts/v1.0.0/app.zip --expires 3600
blob presign s3://reports/report.html --expires 1h --method GET

# Options
--expires DURATION         # Expiration time (seconds or duration like "1h", "30m")
--method GET|PUT           # HTTP method (default: GET)
```

**Boto3 Implementation:**
```python
url = s3.generate_presigned_url(
    'get_object',
    Params={'Bucket': 'artifacts', 'Key': 'v1.0.0/app.zip'},
    ExpiresIn=3600  # 1 hour
)
```

**Output:**
```
https://artifacts.s3.eu-central-1.amazonaws.com/v1.0.0/app.zip?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=...&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=...
```

**Use case:**
```bash
# Share artifact temporarily
url=$(blob presign s3://artifacts/v1.0.0/app.zip --expires 1h)
echo "Download link (valid for 1 hour): $url"

# Upload via presigned URL
upload_url=$(blob presign s3://uploads/data.csv --method PUT --expires 30m)
curl -X PUT -T data.csv "$upload_url"
```

---

### 9. Versioning Operations

#### `versions` - List object versions

**Operation:** `ListObjectVersions`

```bash
blob versions <s3-uri> [OPTIONS]

# Examples
blob versions s3://artifacts/latest.zip
blob versions s3://artifacts/ --recursive

# Options
--recursive / -r           # List versions for all objects with prefix
--limit N                  # Max versions to return
```

**Output (JSON):**
```json
{
  "bucket": "artifacts",
  "key": "latest.zip",
  "versions": [
    {
      "version_id": "abc123",
      "is_latest": true,
      "size": 12345678,
      "last_modified": "2025-11-15T10:30:00Z",
      "etag": "d41d8cd98f00b204e9800998ecf8427e"
    },
    {
      "version_id": "xyz789",
      "is_latest": false,
      "size": 12345000,
      "last_modified": "2025-11-14T10:30:00Z",
      "etag": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
    }
  ]
}
```

---

### 10. Advanced Operations

#### `select` - Query data without downloading

**Operation:** `SelectObjectContent` (S3 Select)

```bash
blob select <s3-uri> <SQL-query> [OPTIONS]

# Examples (CSV)
blob select s3://data/sales.csv "SELECT * FROM s3object WHERE price > 100"

# Examples (JSON)
blob select s3://logs/app.jsonl "SELECT * FROM s3object[*] WHERE level='ERROR'" --format jsonl

# Examples (Parquet)
blob select s3://datasets/data.parquet "SELECT name, age FROM s3object WHERE age > 30" --format parquet

# Options
--format csv|json|jsonl|parquet  # Input format
--output-format csv|json         # Output format (default: same as input)
--compression gzip|bzip2|none    # Input compression
```

**Boto3 Implementation:**
```python
response = s3.select_object_content(
    Bucket='data',
    Key='sales.csv',
    Expression='SELECT * FROM s3object WHERE price > 100',
    ExpressionType='SQL',
    InputSerialization={
        'CSV': {'FileHeaderInfo': 'USE', 'RecordDelimiter': '\n', 'FieldDelimiter': ','},
        'CompressionType': 'NONE'
    },
    OutputSerialization={'CSV': {}}
)

# Stream results
for event in response['Payload']:
    if 'Records' in event:
        print(event['Records']['Payload'].decode())
```

**Use case:**
```bash
# Query large CSV without downloading entire file
blob select s3://logs/access.csv \
  "SELECT COUNT(*) FROM s3object WHERE status_code = 500" \
  --format csv

# Filter JSON logs
blob select s3://logs/app.jsonl \
  "SELECT timestamp, message FROM s3object[*] WHERE level='ERROR' AND timestamp > '2025-11-15T00:00:00'" \
  --format jsonl
```

---

## CLI Command Specifications

### Command Structure

**Pattern:** `blob <operation> [arguments] [options]`

```bash
# Upload/Download
blob put <local> <s3-uri>          # Upload file
blob get <s3-uri> <local>          # Download file
blob put-dir <local-dir> <s3-prefix>  # Upload directory
blob get-dir <s3-prefix> <local-dir>  # Download directory

# List/Search
blob list <s3-prefix>              # List objects
blob versions <s3-uri>             # List versions

# Modify
blob delete <s3-uri>               # Delete object
blob copy <src-s3-uri> <dst-s3-uri>  # Copy object
blob sync <src> <dst>              # Sync directory

# Metadata
blob head <s3-uri>                 # Get metadata
blob tag <s3-uri> KEY=VALUE        # Add tags
blob untag <s3-uri>                # Remove tags

# Advanced
blob presign <s3-uri>              # Generate presigned URL
blob select <s3-uri> <sql>         # Query data
```

### Global Options

**Available on all commands:**

```bash
--bucket BUCKET            # Default bucket (or BLOB_BUCKET env var)
--region REGION            # AWS region (or AWS_REGION env var)
--profile PROFILE          # AWS profile (or AWS_PROFILE env var)
--format json|text|table   # Output format (default: json)
--verbose / -V             # Verbose output (stderr)
--quiet / -q               # Suppress output
--dry-run / -n             # Show what would happen (no actual operations)
```

### Environment Variables

```bash
# Primary configuration
export BLOB_BUCKET=claude-code-artifacts
export AWS_REGION=eu-central-1
export AWS_PROFILE=default

# Optional
export BLOB_STORAGE_CLASS=STANDARD          # Default storage class
export BLOB_MULTIPART_THRESHOLD=104857600   # 100MB threshold for multipart
export BLOB_CHUNK_SIZE=104857600            # 100MB chunk size
export BLOB_MAX_CONCURRENCY=10              # Max parallel operations
```

### Agent-Friendly Help Examples

**Every command includes self-documenting examples:**

```python
@click.command('put')
def put():
    """Upload file or stdin to S3.

    Automatically uses multipart upload for files >100MB with parallel
    chunk uploads for optimal performance.

    Examples:

    \b
        # Upload file
        blob put ./build/app.zip s3://artifacts/v1.0.0/app.zip

    \b
        # Upload from stdin
        cat report.json | blob put - s3://reports/daily/$(date +%s).json

    \b
        # Upload with metadata and tags
        blob put ./app.zip s3://artifacts/latest.zip \\
            --metadata version=1.0.0 \\
            --metadata build=123 \\
            --tags env=prod,project=claude-code

    \b
        # Upload with custom storage class
        blob put ./archive.tar.gz s3://archives/data.tar.gz \\
            --storage-class GLACIER

    \b
    Output Format:
        Returns JSON with upload details:
        {
          "bucket": "artifacts",
          "key": "v1.0.0/app.zip",
          "size": 12345678,
          "etag": "d41d8cd98f00b204e9800998ecf8427e",
          "version_id": "abc123"
        }
    """
    pass
```

---

## Implementation Architecture

### Project Structure

```
aws_primitives_tool/
├── cli.py                          # Main CLI entry point
├── blob/
│   ├── __init__.py                 # Public API exports
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── upload_commands.py      # put, put-dir
│   │   ├── download_commands.py    # get, get-dir
│   │   ├── list_commands.py        # list, versions
│   │   ├── delete_commands.py      # delete
│   │   ├── copy_commands.py        # copy, sync
│   │   ├── metadata_commands.py    # head, tag, untag
│   │   ├── presign_commands.py     # presign
│   │   └── select_commands.py      # select
│   ├── core/
│   │   ├── __init__.py
│   │   ├── client.py               # S3 client wrapper
│   │   ├── upload.py               # Upload operations (multipart)
│   │   ├── download.py             # Download operations (streaming)
│   │   ├── sync.py                 # Sync operations
│   │   ├── metadata.py             # Metadata operations
│   │   └── select.py               # S3 Select operations
│   ├── models.py                   # Type models (S3Object, etc.)
│   ├── exceptions.py               # Custom exceptions
│   └── utils.py                    # Shared utilities (path parsing, etc.)
└── utils.py                        # Global utilities
```

### Type Definitions (models.py)

```python
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class S3Object:
    """S3 object model."""
    bucket: str
    key: str
    size: int
    etag: str
    last_modified: datetime
    storage_class: str = 'STANDARD'
    version_id: Optional[str] = None
    metadata: dict[str, str] = None
    tags: dict[str, str] = None

@dataclass
class S3URI:
    """Parsed S3 URI."""
    bucket: str
    key: str

    @classmethod
    def parse(cls, uri: str) -> 'S3URI':
        """Parse s3://bucket/key URI."""
        if not uri.startswith('s3://'):
            raise ValueError(f"Invalid S3 URI: {uri}")
        parts = uri[5:].split('/', 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ''
        return cls(bucket=bucket, key=key)

    def __str__(self) -> str:
        return f"s3://{self.bucket}/{self.key}"

@dataclass
class UploadResult:
    """Result of upload operation."""
    bucket: str
    key: str
    size: int
    etag: str
    version_id: Optional[str] = None
    storage_class: str = 'STANDARD'
    uploaded_at: datetime = None
```

### Exception Hierarchy (exceptions.py)

```python
class BlobError(Exception):
    """Base exception for blob operations."""
    pass

class ObjectNotFoundError(BlobError):
    """S3 object does not exist."""
    pass

class BucketNotFoundError(BlobError):
    """S3 bucket does not exist."""
    pass

class InvalidURIError(BlobError):
    """Invalid S3 URI format."""
    pass

class UploadFailedError(BlobError):
    """Upload operation failed."""
    pass

class DownloadFailedError(BlobError):
    """Download operation failed."""
    pass

class AWSThrottlingError(BlobError):
    """S3 throttling occurred."""
    pass

class AWSPermissionError(BlobError):
    """AWS permission denied."""
    pass
```

### S3 Client (core/client.py)

```python
import boto3
from typing import Optional
from botocore.exceptions import ClientError
from ..models import S3URI

class S3Client:
    """S3 client wrapper with error handling."""

    def __init__(
        self,
        region: Optional[str] = None,
        profile: Optional[str] = None
    ):
        session = boto3.Session(profile_name=profile, region_name=region)
        self.s3 = session.client('s3')
        self.region = region or session.region_name

    def put_object(
        self,
        bucket: str,
        key: str,
        body: bytes,
        metadata: Optional[dict] = None,
        tags: Optional[dict] = None,
        storage_class: str = 'STANDARD',
        content_type: Optional[str] = None
    ) -> dict:
        """Put object to S3."""
        try:
            kwargs = {
                'Bucket': bucket,
                'Key': key,
                'Body': body,
                'StorageClass': storage_class
            }
            if metadata:
                kwargs['Metadata'] = metadata
            if content_type:
                kwargs['ContentType'] = content_type
            if tags:
                kwargs['Tagging'] = '&'.join([f'{k}={v}' for k, v in tags.items()])

            response = self.s3.put_object(**kwargs)
            return response
        except ClientError as e:
            self._handle_error(e)

    def get_object(
        self,
        bucket: str,
        key: str,
        version_id: Optional[str] = None,
        byte_range: Optional[str] = None
    ) -> dict:
        """Get object from S3."""
        try:
            kwargs = {'Bucket': bucket, 'Key': key}
            if version_id:
                kwargs['VersionId'] = version_id
            if byte_range:
                kwargs['Range'] = f'bytes={byte_range}'

            response = self.s3.get_object(**kwargs)
            return response
        except ClientError as e:
            self._handle_error(e)

    def _handle_error(self, error: ClientError) -> None:
        """Convert boto3 errors to blob exceptions."""
        code = error.response['Error']['Code']

        if code == 'NoSuchKey':
            raise ObjectNotFoundError(f"Object not found: {error}")
        elif code == 'NoSuchBucket':
            raise BucketNotFoundError(f"Bucket not found: {error}")
        elif code == 'SlowDown' or code == '503 SlowDown':
            raise AWSThrottlingError("S3 throttling - retry with backoff")
        elif code == 'AccessDenied':
            raise AWSPermissionError("AWS permission denied")
        else:
            raise BlobError(f"S3 error: {error}")
```

### Multipart Upload (core/upload.py)

```python
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

MULTIPART_THRESHOLD = 100 * 1024 * 1024  # 100MB
CHUNK_SIZE = 100 * 1024 * 1024  # 100MB per part

def upload_file(
    client: S3Client,
    local_path: str,
    bucket: str,
    key: str,
    storage_class: str = 'STANDARD',
    metadata: Optional[dict] = None,
    tags: Optional[dict] = None,
    progress_callback: Optional[callable] = None
) -> dict:
    """Upload file with automatic multipart for large files."""
    file_size = os.path.getsize(local_path)

    if file_size < MULTIPART_THRESHOLD:
        # Single PUT
        with open(local_path, 'rb') as f:
            return client.put_object(
                bucket=bucket,
                key=key,
                body=f.read(),
                storage_class=storage_class,
                metadata=metadata,
                tags=tags
            )
    else:
        # Multipart upload
        return multipart_upload(
            client=client,
            local_path=local_path,
            bucket=bucket,
            key=key,
            storage_class=storage_class,
            metadata=metadata,
            tags=tags,
            chunk_size=CHUNK_SIZE,
            progress_callback=progress_callback
        )

def multipart_upload(
    client: S3Client,
    local_path: str,
    bucket: str,
    key: str,
    storage_class: str,
    metadata: Optional[dict],
    tags: Optional[dict],
    chunk_size: int,
    progress_callback: Optional[callable]
) -> dict:
    """Perform multipart upload with parallel chunk uploads."""
    # Step 1: Initiate multipart upload
    kwargs = {
        'Bucket': bucket,
        'Key': key,
        'StorageClass': storage_class
    }
    if metadata:
        kwargs['Metadata'] = metadata
    if tags:
        kwargs['Tagging'] = '&'.join([f'{k}={v}' for k, v in tags.items()])

    response = client.s3.create_multipart_upload(**kwargs)
    upload_id = response['UploadId']

    try:
        # Step 2: Upload parts in parallel
        file_size = os.path.getsize(local_path)
        num_parts = (file_size + chunk_size - 1) // chunk_size

        parts = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {}
            with open(local_path, 'rb') as f:
                for part_num in range(1, num_parts + 1):
                    chunk = f.read(chunk_size)
                    future = executor.submit(
                        upload_part,
                        client,
                        bucket,
                        key,
                        upload_id,
                        part_num,
                        chunk
                    )
                    futures[future] = part_num

            # Collect results
            for future in as_completed(futures):
                part_num = futures[future]
                etag = future.result()
                parts.append({'PartNumber': part_num, 'ETag': etag})

                if progress_callback:
                    progress_callback(part_num, num_parts)

        # Sort parts by part number
        parts.sort(key=lambda p: p['PartNumber'])

        # Step 3: Complete multipart upload
        response = client.s3.complete_multipart_upload(
            Bucket=bucket,
            Key=key,
            UploadId=upload_id,
            MultipartUpload={'Parts': parts}
        )

        return response

    except Exception as e:
        # Abort multipart upload on failure
        client.s3.abort_multipart_upload(
            Bucket=bucket,
            Key=key,
            UploadId=upload_id
        )
        raise UploadFailedError(f"Multipart upload failed: {e}")

def upload_part(
    client: S3Client,
    bucket: str,
    key: str,
    upload_id: str,
    part_number: int,
    chunk: bytes
) -> str:
    """Upload a single part."""
    response = client.s3.upload_part(
        Bucket=bucket,
        Key=key,
        UploadId=upload_id,
        PartNumber=part_number,
        Body=chunk
    )
    return response['ETag']
```

---

## Error Handling

### Error Categories

1. **User Errors (Exit 1):**
   - Object not found
   - Bucket not found
   - Invalid S3 URI

2. **Invalid Arguments (Exit 2):**
   - Missing required arguments
   - Invalid path format
   - Invalid storage class

3. **AWS Errors (Exit 3):**
   - S3 throttling (503 SlowDown)
   - Permission denied
   - Network errors
   - Upload/download failures

### Error Message Format

**Structure:**

```
Error: <concise description>

Solution: <actionable remedy>

Details (optional):
  - <additional context>
```

**Examples:**

```bash
# Object not found
Error: Object "s3://artifacts/missing.zip" does not exist

Solution: Use 'blob list s3://artifacts/' to see available objects or check the key name

# Bucket not found
Error: Bucket "invalid-bucket" does not exist

Solution: Create bucket with 'aws s3 mb s3://invalid-bucket' or check bucket name

# Permission denied
Error: Access denied for operation PutObject on s3://artifacts/app.zip

Solution: Check IAM permissions. Required: s3:PutObject on bucket "artifacts"

Details:
  - Current IAM role: arn:aws:iam::123456789:role/claude-code
  - Required permissions: s3:PutObject, s3:PutObjectTagging

# Throttling
Error: S3 throttling (503 SlowDown) - request rate exceeded

Solution: Retry with exponential backoff. Reduce --parallel option to limit concurrent requests.

Details:
  - Current parallel uploads: 10
  - Recommended: --parallel 5
```

---

## Use Cases & Examples

### Use Case 1: Session History Persistence

**Problem:** Save Claude Code session history for audit and replay.

```bash
# Save session history (JSONL format)
cat session.jsonl | blob put - s3://artifacts/sessions/$(date +%Y-%m-%d)/session-$SESSION_ID.jsonl \
  --metadata session_id=$SESSION_ID \
  --metadata timestamp=$(date -u +%s) \
  --tags project=claude-code,type=session

# Retrieve session history
blob get s3://artifacts/sessions/2025-11-15/session-123.jsonl - | jq '.messages[]'

# List recent sessions
blob list s3://artifacts/sessions/ --since "7 days ago" --format keys
```

### Use Case 2: Build Artifact Distribution

**Problem:** Store and distribute build artifacts across team.

```bash
# Upload build artifacts
VERSION="v1.0.0"
blob put-dir ./dist/ s3://artifacts/$VERSION/ \
  --metadata version=$VERSION \
  --metadata commit=$GIT_COMMIT \
  --tags env=prod,released=true

# Generate shareable download links
blob presign s3://artifacts/$VERSION/app.zip --expires 24h

# Download latest artifacts
blob get-dir s3://artifacts/latest/ ./downloaded/
```

### Use Case 3: Dataset Sharing

**Problem:** Share large datasets between agents without re-uploading.

```bash
# Agent 1: Upload dataset once
blob put dataset.parquet s3://shared/datasets/training-data.parquet \
  --storage-class STANDARD_IA \
  --metadata created_by=agent-1 \
  --metadata rows=1000000

# Agent 2-10: Download and use
blob get s3://shared/datasets/training-data.parquet ./data/training.parquet

# Query dataset without downloading (S3 Select)
blob select s3://shared/datasets/training-data.parquet \
  "SELECT category, COUNT(*) FROM s3object GROUP BY category" \
  --format parquet
```

### Use Case 4: Log Aggregation

**Problem:** Centralize logs from distributed agents.

```bash
# Each agent streams logs to S3
tail -f app.log | while read line; do
  echo "$line" | blob put - s3://logs/$(date +%Y-%m-%d)/agent-$AGENT_ID.log --append
done

# Alternative: Batch upload every hour
blob put app.log s3://logs/$(date +%Y-%m-%d-%H)/agent-$AGENT_ID.log

# Query logs across all agents
blob list s3://logs/$(date +%Y-%m-%d)/ --format keys | while read key; do
  blob select "s3://logs/$key" \
    "SELECT * FROM s3object WHERE level='ERROR'" \
    --format jsonl
done > errors-$(date +%Y-%m-%d).json
```

### Use Case 5: Checkpoint/Resume

**Problem:** Save agent state for fault tolerance.

```bash
# Save checkpoint every 10 minutes
while true; do
  state=$(serialize-agent-state.sh)
  echo "$state" | blob put - s3://checkpoints/agent-$AGENT_ID/checkpoint-$(date +%s).json \
    --metadata agent_id=$AGENT_ID \
    --metadata timestamp=$(date -u +%s)
  sleep 600
done &

# Resume from latest checkpoint on crash
latest=$(blob list s3://checkpoints/agent-$AGENT_ID/ --format keys | tail -1)
blob get "s3://logs/$latest" - | restore-agent-state.sh
```

### Use Case 6: Backup and Restore

**Problem:** Backup workspace, restore on different machine.

```bash
# Backup workspace
blob sync ./workspace/ s3://backup/workspace-$(date +%Y-%m-%d)/ \
  --exclude ".git" \
  --exclude "node_modules" \
  --exclude "__pycache__"

# Restore on different machine
blob sync s3://backup/workspace-2025-11-15/ ./restored-workspace/

# Incremental backup (only changed files)
blob sync ./workspace/ s3://backup/workspace-latest/ \
  --delete  # Remove files deleted from workspace
```

### Use Case 7: Event-Driven Processing

**Problem:** Trigger Lambda when files uploaded to S3.

```bash
# Enable EventBridge for bucket (one-time setup)
aws s3api put-bucket-notification-configuration \
  --bucket artifacts \
  --notification-configuration '{
    "EventBridgeConfiguration": {}
  }'

# Upload file (triggers EventBridge → Lambda)
blob put report.csv s3://artifacts/reports/$(date +%s).csv

# EventBridge rule routes to Lambda
# Lambda receives event:
{
  "detail-type": "Object Created",
  "source": "aws.s3",
  "detail": {
    "bucket": {"name": "artifacts"},
    "object": {"key": "reports/1731696000.csv"}
  }
}
```

### Use Case 8: Versioned Configuration

**Problem:** Track configuration changes over time.

```bash
# Upload configuration with versioning enabled
blob put config.yaml s3://config/app-config.yaml \
  --metadata version=1.0 \
  --metadata updated_by=$(whoami)

# List all versions
blob versions s3://config/app-config.yaml

# Rollback to previous version
blob copy s3://config/app-config.yaml?versionId=abc123 \
  s3://config/app-config.yaml

# Download specific version
blob get s3://config/app-config.yaml --version-id abc123 ./config.yaml
```

---

## Cost Analysis

### S3 Pricing (EU: eu-central-1)

**Storage:**

| Storage Class | Cost (GB-month) | Minimum Duration | Use Case |
|--------------|----------------|------------------|----------|
| **STANDARD** | $0.023 | None | Frequent access |
| **STANDARD_IA** | $0.0125 | 30 days | Infrequent access |
| **GLACIER** | $0.0040 | 90 days | Archive (hours retrieval) |
| **GLACIER_DEEP_ARCHIVE** | $0.00099 | 180 days | Long-term archive (12h retrieval) |

**Requests:**

| Operation | Cost | Notes |
|-----------|------|-------|
| **PUT** | $0.005/1,000 | Upload |
| **GET** | $0.0004/1,000 | Download |
| **LIST** | $0.005/1,000 | List objects |
| **DELETE** | FREE | Delete objects |

**Data Transfer:**

| Transfer Type | Cost | Notes |
|--------------|------|-------|
| **Upload (IN)** | FREE | All uploads |
| **Download to Internet (OUT)** | $0.09/GB | First 10TB/month |
| **Download to AWS services (same region)** | FREE | S3 → Lambda, EC2, etc. |
| **Download to CloudFront** | FREE | S3 → CDN |

### Example Cost Calculations

**Scenario 1: Session History (100GB/month)**

```
Storage:
  - 100 GB × $0.023/GB = $2.30/month

Requests:
  - 10,000 PUT (sessions) × $0.005/1k = $0.05
  - 50,000 GET (reads) × $0.0004/1k = $0.02
  - 1,000 LIST × $0.005/1k = $0.005

Data Transfer:
  - 10 GB download to Lambda (same region) = FREE

Total: $2.37/month
```

**Scenario 2: Build Artifacts (50GB, infrequent access)**

```
Storage (STANDARD_IA after 30 days):
  - First 30 days: 50 GB × $0.023 × (30/30) = $1.15
  - After 30 days: 50 GB × $0.0125 = $0.625/month

Requests:
  - 1,000 PUT (builds) × $0.005/1k = $0.005
  - 5,000 GET (downloads) × $0.0004/1k = $0.002
  - Retrieval from IA: 5 GB × $0.01/GB = $0.05

Total: ~$0.68/month (after transition to IA)
```

**Scenario 3: Log Aggregation (500GB/month, 90-day retention)**

```
Storage (with lifecycle to Glacier after 30 days):
  - STANDARD (0-30 days): 167 GB avg × $0.023 = $3.84
  - GLACIER (30-90 days): 333 GB avg × $0.0040 = $1.33

Requests:
  - 100,000 PUT (logs) × $0.005/1k = $0.50
  - 10,000 GET × $0.0004/1k = $0.004
  - 10,000 LIST × $0.005/1k = $0.05

Data Transfer:
  - 50 GB to Lambda = FREE

Total: ~$5.72/month
```

### Cost Optimization Tips

1. **Use Lifecycle Policies:**
   ```bash
   # Transition to IA after 30 days, Glacier after 90 days
   aws s3api put-bucket-lifecycle-configuration --bucket artifacts --lifecycle-configuration '{
     "Rules": [{
       "Status": "Enabled",
       "Transitions": [
         {"Days": 30, "StorageClass": "STANDARD_IA"},
         {"Days": 90, "StorageClass": "GLACIER"}
       ]
     }]
   }'
   ```

2. **Use Intelligent-Tiering for Unpredictable Access:**
   - Automatically moves objects between access tiers
   - Cost: $0.023/GB + $0.0025/1k objects monitoring fee
   - Saves money if access patterns vary

3. **Compress Before Upload:**
   ```bash
   # Reduce storage and transfer costs
   gzip -c large-file.csv | blob put - s3://data/large-file.csv.gz
   ```

4. **Use S3 Select to Reduce Transfer:**
   ```bash
   # Query 100GB file, retrieve only 1MB of results
   blob select s3://logs/huge-file.csv "SELECT * FROM s3object WHERE error=true"
   # Transfer cost: 1MB vs 100GB (1000x savings)
   ```

5. **Delete Old Versions:**
   ```bash
   # Set expiration for non-current versions
   aws s3api put-bucket-lifecycle-configuration --bucket artifacts --lifecycle-configuration '{
     "Rules": [{
       "Status": "Enabled",
       "NoncurrentVersionExpiration": {"NoncurrentDays": 90}
     }]
   }'
   ```

---

## Testing Strategy

### Unit Tests (pytest)

**Test Core Operations:**

```python
# tests/blob/test_upload.py
import pytest
from aws_primitives_tool.blob.core.upload import upload_file
from unittest.mock import MagicMock

def test_upload_small_file(tmp_path):
    """Test single PUT for small file."""
    # Create test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello, World!")

    client = MagicMock()
    client.put_object.return_value = {'ETag': 'abc123'}

    result = upload_file(
        client=client,
        local_path=str(test_file),
        bucket='test-bucket',
        key='test.txt'
    )

    assert result['ETag'] == 'abc123'
    client.put_object.assert_called_once()

def test_upload_large_file_uses_multipart(tmp_path):
    """Test multipart upload for large file."""
    # Create 200MB test file
    test_file = tmp_path / "large.bin"
    test_file.write_bytes(b'0' * (200 * 1024 * 1024))

    client = MagicMock()
    # Mock multipart upload responses
    client.s3.create_multipart_upload.return_value = {'UploadId': 'upload-123'}
    client.s3.upload_part.return_value = {'ETag': 'part-abc'}
    client.s3.complete_multipart_upload.return_value = {'ETag': 'final-abc'}

    result = upload_file(
        client=client,
        local_path=str(test_file),
        bucket='test-bucket',
        key='large.bin'
    )

    # Verify multipart was used
    client.s3.create_multipart_upload.assert_called_once()
    assert client.s3.upload_part.call_count == 2  # 200MB / 100MB chunks = 2 parts
    client.s3.complete_multipart_upload.assert_called_once()
```

### Integration Tests (pytest + moto)

**Test Against Mock S3:**

```python
# tests/blob/test_integration.py
import pytest
import boto3
from moto import mock_aws

@mock_aws
def test_upload_and_download_roundtrip():
    """Test upload → download roundtrip."""
    # Create mock S3 bucket
    s3 = boto3.client('s3', region_name='us-east-1')
    s3.create_bucket(Bucket='test-bucket')

    # Upload
    from aws_primitives_tool.blob.core.client import S3Client
    from aws_primitives_tool.blob.core.upload import upload_file

    client = S3Client()
    test_data = b"Hello, World!"

    with open('/tmp/test.txt', 'wb') as f:
        f.write(test_data)

    upload_file(
        client=client,
        local_path='/tmp/test.txt',
        bucket='test-bucket',
        key='test.txt'
    )

    # Download
    from aws_primitives_tool.blob.core.download import download_file

    download_file(
        client=client,
        bucket='test-bucket',
        key='test.txt',
        local_path='/tmp/downloaded.txt'
    )

    # Verify
    with open('/tmp/downloaded.txt', 'rb') as f:
        assert f.read() == test_data
```

### CLI Tests (Click CliRunner)

**Test CLI Commands:**

```python
# tests/blob/test_cli.py
from click.testing import CliRunner
from aws_primitives_tool.cli import cli

def test_put_command(mock_s3_bucket, tmp_path):
    """Test put command."""
    # Create test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello, World!")

    runner = CliRunner()
    result = runner.invoke(cli, [
        'blob', 'put',
        str(test_file),
        's3://test-bucket/test.txt'
    ])

    assert result.exit_code == 0
    assert 'test.txt' in result.output

def test_get_command(mock_s3_bucket_with_object, tmp_path):
    """Test get command."""
    download_path = tmp_path / "downloaded.txt"

    runner = CliRunner()
    result = runner.invoke(cli, [
        'blob', 'get',
        's3://test-bucket/test.txt',
        str(download_path)
    ])

    assert result.exit_code == 0
    assert download_path.exists()
```

### End-to-End Tests

**Test Real S3 Operations:**

```bash
# tests/e2e/test_blob_workflow.sh
#!/usr/bin/env bash
set -e

# Setup
export TEST_BUCKET=e2e-test-$(date +%s)
aws s3 mb s3://$TEST_BUCKET

# Test: Upload file
echo "Test data" > test.txt
blob put test.txt s3://$TEST_BUCKET/test.txt

# Test: Download file
blob get s3://$TEST_BUCKET/test.txt downloaded.txt
diff test.txt downloaded.txt

# Test: List objects
blob list s3://$TEST_BUCKET/ | jq -e '.objects[0].key == "test.txt"'

# Test: Delete object
blob delete s3://$TEST_BUCKET/test.txt
! blob head s3://$TEST_BUCKET/test.txt  # Should fail

# Cleanup
aws s3 rb s3://$TEST_BUCKET --force
rm test.txt downloaded.txt
```

### Performance Tests

**Measure Upload/Download Speed:**

```python
# tests/performance/test_throughput.py
import time
from aws_primitives_tool.blob.core.upload import upload_file
from aws_primitives_tool.blob.core.client import S3Client

def test_upload_throughput():
    """Measure upload throughput for large file."""
    client = S3Client()

    # Create 1GB test file
    test_file = '/tmp/1gb-test.bin'
    with open(test_file, 'wb') as f:
        f.write(b'0' * (1024 * 1024 * 1024))

    # Measure upload time
    start = time.time()
    upload_file(
        client=client,
        local_path=test_file,
        bucket='perf-test',
        key='1gb-test.bin'
    )
    elapsed = time.time() - start

    throughput_mbps = (1024 / elapsed) * 8
    print(f"Upload throughput: {throughput_mbps:.2f} Mbps ({elapsed:.2f}s for 1GB)")

    # Expect at least 100 Mbps
    assert throughput_mbps > 100, f"Throughput too low: {throughput_mbps:.2f} Mbps"
```

---

## Next Steps

### Phase 1: Foundation (Week 1)
- [ ] Implement S3 client wrapper with error handling
- [ ] Implement upload operations (put, put-dir, multipart)
- [ ] Implement download operations (get, get-dir, streaming)
- [ ] Add unit tests for core operations
- [ ] Create CLI commands for upload/download

### Phase 2: List & Metadata (Week 2)
- [ ] Implement list operations (list, versions)
- [ ] Implement metadata operations (head, tag, untag)
- [ ] Implement delete operations (delete, delete with prefix)
- [ ] Add integration tests with moto
- [ ] Create CLI commands for list/metadata/delete

### Phase 3: Advanced Operations (Week 3)
- [ ] Implement copy operations (copy, sync algorithm)
- [ ] Implement presigned URL generation
- [ ] Implement S3 Select operations
- [ ] Add end-to-end tests with real S3
- [ ] Performance benchmarks

### Phase 4: Polish & Documentation (Week 4)
- [ ] Optimize multipart uploads (parallel chunks)
- [ ] Add progress bars for long operations
- [ ] Comprehensive error handling with solutions
- [ ] Update README.md with usage examples
- [ ] Update CLAUDE.md with references to design docs
- [ ] Release v0.2.0 (blob + kvstore primitives)

---

## References

### S3 Documentation
- [S3 Developer Guide](https://docs.aws.amazon.com/s3/latest/userguide/)
- [S3 Best Practices](https://docs.aws.amazon.com/s3/latest/userguide/optimizing-performance.html)
- [S3 Multipart Upload](https://docs.aws.amazon.com/s3/latest/userguide/mpuoverview.html)
- [S3 Select](https://docs.aws.amazon.com/s3/latest/userguide/selecting-content-from-objects.html)
- [S3 Lifecycle Policies](https://docs.aws.amazon.com/s3/latest/userguide/object-lifecycle-mgmt.html)
- [S3 Event Notifications](https://docs.aws.amazon.com/s3/latest/userguide/EventBridge.html)

### AWS Pricing
- [S3 Pricing (EU Regions)](https://aws.amazon.com/s3/pricing/)
- [S3 Storage Classes](https://aws.amazon.com/s3/storage-classes/)

### Related Tools
- [AWS CLI S3 Commands](https://docs.aws.amazon.com/cli/latest/reference/s3/) - Inspiration for CLI design
- [rclone](https://rclone.org/) - Multi-cloud sync tool patterns
- [s5cmd](https://github.com/peak/s5cmd) - Fast S3 CLI reference

---

**Document Version:** 1.0
**Last Updated:** 2025-11-15
**Status:** Ready for Implementation
**Next Review:** After Phase 1 Completion
