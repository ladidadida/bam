# Bam + cascache Integration Tests

This directory contains integration tests that verify bam works correctly with a real cascache server.

## Overview

These tests use Docker Compose to:
1. Start a cascache server in a container
2. Run bam tests against the real server
3. Verify upload, download, and cache sharing functionality

## Prerequisites

- Docker and Docker Compose installed
- No need to install cascache locally (runs in container via PyPI)

## Running Tests

### Full Integration Test Suite

```bash
# From project root
docker compose -f tests/integration-cascache/docker-compose.yml up --abort-on-container-exit

# Clean up after tests
docker compose -f tests/integration-cascache/docker-compose.yml down -v
```

### Run Specific Tests

```bash
# Start cascache server in background
docker compose -f tests/integration-cascache/docker-compose.yml up -d cascache

# Wait for cascache to be ready
docker compose -f tests/integration-cascache/docker-compose.yml exec cascache python -c "import socket; s = socket.socket(); s.connect(('localhost', 50051)); s.close()"

# Run specific test
docker compose -f tests/integration-cascache/docker-compose.yml run --rm bam-client \
  sh -c "pip install uv && uv sync && uv run pytest tests/integration-cascache/test_cascache_integration.py::test_cascache_upload_download -v"

# Clean up
docker compose -f tests/integration-cascache/docker-compose.yml down -v
```

### Local Development (with local cascache)

If you have cascache installed locally:

```bash
# Terminal 1: Start cascache server
pip install cascache
python -m cascache

# Terminal 2: Run tests
BAM_CAS_URL=grpc://localhost:50051 uv run pytest tests/integration-cascache/test_cascache_integration.py -v
```

## Test Coverage

The integration tests verify:

- ✅ **Upload/Download**: Basic artifact storage and retrieval
- ✅ **Exists Check**: Verify artifacts exist in remote cache
- ✅ **CacheManager Integration**: Full local+remote cache hierarchy
- ✅ **Multi-File Artifacts**: Handle multiple files in one cache entry
- ✅ **Cache Sharing**: Simulate multiple machines sharing cache
- ✅ **Large Files**: Handle files >1MB (tests streaming behavior)
- ✅ **Retry Logic**: Verify automatic retry with real network

## Test Structure

```
tests/integration-cascache/
├── docker-compose.yml          # Container orchestration
├── test_cascache_integration.py   # Integration test suite
└── README.md                    # This file
```

## CI Integration

See `.github/workflows/cascache-integration.yml` for CI configuration.

## Troubleshooting

### cascache server not starting

Check logs:
```bash
docker compose -f tests/integration-cascache/docker-compose.yml logs cascache
```

### Connection refused

Ensure cascache health check passes:
```bash
docker compose -f tests/integration-cascache/docker-compose.yml ps
```

The `cascache` service should show as "healthy".

### Tests timing out

Increase timeouts in `test_cascache_integration.py` or check cascache logs for errors.

## Development

To add new integration tests:

1. Add test function to `test_cascache_integration.py`
2. Use `cascache_url` fixture for server URL
3. Use `local_cache` fixture for local cache instance
4. Always call `await cas_cache.close()` in finally block
5. Test should be fully self-contained (create/cleanup own artifacts)

## References

- cascache_server GitLab: https://gitlab.com/cascascade/cascache_server
- cascache_lib: https://gitlab.com/cascascade/cascache_lib
- Remote Execution API: https://github.com/bazelbuild/remote-apis
- Bam remote cache docs: ../../examples/remote-cache/README.md
