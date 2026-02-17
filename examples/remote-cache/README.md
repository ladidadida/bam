# Cascade Example - Remote CAS Cache

This example demonstrates how to configure Cascade with remote CAS caching.

## Configuration

```yaml
version: 1

# Cache configuration with both local and remote
cache:
  local:
    enabled: true
    path: .cascade/cache  # Local cache directory
  
  remote:
    enabled: true
    type: cas
    url: grpc://localhost:50051  # cascache server URL
    token_file: ~/.cascade/cas-token  # Optional authentication token
    upload: true   # Automatically upload to remote
    download: true # Automatically download from remote
    timeout: 30.0  # Request timeout in seconds

tasks:
  build:
    inputs:
      - "src/**/*.py"
    outputs:
      - "dist/"
    command: python -m build

  test:
    inputs:
      - "tests/**/*.py"
      - "src/**/*.py"
    command: pytest
    depends_on:
      - build
```

## Cache Behavior

**On cache miss (first run):**
1. Task executes normally
2. Outputs stored in local cache (`.cascade/cache`)
3. Outputs automatically uploaded to remote CAS server

**On cache hit (subsequent runs):**
1. Check local cache first (fast)
2. If not in local, check remote CAS
3. If found in remote, download and populate local cache
4. Restore outputs without executing task

**On remote CAS failure:**
- Gracefully falls back to local cache only
- Logs warnings but doesn't fail workflow
- Automatic retry logic with exponential backoff
- Connection pooling for efficient gRPC connections

## Retry Logic & Error Handling

Cascade provides robust error handling for remote cache operations:

**Automatic Retries:**
- Transient errors (network issues, timeouts) are retried automatically
- Default: 3 retry attempts with exponential backoff
- Initial backoff: 100ms, doubles after each retry (up to 5 seconds)
- Non-retryable errors (authentication, invalid requests) fail immediately

**Connection Pooling:**
- gRPC connections are reused with keepalive
- Automatic reconnection on network failures
- Efficient for high-throughput workflows

**Error Types:**
- `UNAVAILABLE`: Server unreachable → Retry with backoff
- `DEADLINE_EXCEEDED`: Timeout → Retry with backoff
- `RESOURCE_EXHAUSTED`: Server overloaded → Retry with backoff
- `UNAUTHENTICATED`: Invalid token → Fail immediately (check token)
- `PERMISSION_DENIED`: Insufficient privileges → Fail immediately

**Configuration:**
```yaml
cache:
  remote:
    enabled: true
    type: cas
    url: grpc://localhost:50051
    timeout: 30.0          # Request timeout (default: 30s)
    max_retries: 3         # Retry attempts (default: 3)
    initial_backoff: 0.1   # Initial delay (default: 0.1s)
```

## cascache Server Setup

To run a local cascache server:

```bash
# Start cascache server
cascache serve --host 0.0.0.0 --port 50051

# With authentication
cascache token create > ~/.cascade/cas-token
cascache serve --token-file ~/.cascade/cas-token
```

## Local-Only Mode

To disable remote caching:

```yaml
cache:
  local:
    enabled: true
    path: .cascade/cache
  
  remote:
    enabled: false  # Disable remote cache
```

Or use `--no-cache` flag to disable all caching:

```bash
cascade run build --no-cache
```

## Cache Statistics

Future enhancement: View cache hit/miss statistics

```bash
cascade cache stats
```

Example output:
```
Cache Statistics:
  Local hits:     45  (90%)
  Remote hits:     5  (10%)
  Misses:          0  (0%)
  Total requests: 50
  Hit rate:      100%

Remote uploads:         3
Remote upload failures: 0
Remote download failures: 0
```
