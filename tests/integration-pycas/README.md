# Cascade + pycas Integration Tests

This directory contains integration tests that verify Cascade works correctly with a real pycas server.

## Overview

These tests use Docker Compose to:
1. Start a pycas server in a container
2. Run Cascade tests against the real server
3. Verify upload, download, and cache sharing functionality

## Prerequisites

- Docker and Docker Compose installed
- No need to install pycas locally (runs in container via `uv run --from git+...`)

## Running Tests

### Full Integration Test Suite

```bash
# From project root
docker compose -f tests/integration-pycas/docker-compose.yml up --abort-on-container-exit

# Clean up after tests
docker compose -f tests/integration-pycas/docker-compose.yml down -v
```

### Run Specific Tests

```bash
# Start pycas server in background
docker compose -f tests/integration-pycas/docker-compose.yml up -d pycas

# Wait for pycas to be ready
docker compose -f tests/integration-pycas/docker-compose.yml exec pycas python -c "import socket; s = socket.socket(); s.connect(('localhost', 50051)); s.close()"

# Run specific test
docker compose -f tests/integration-pycas/docker-compose.yml run --rm cascade-client \
  sh -c "pip install uv && uv sync && uv run pytest tests/integration-pycas/test_pycas_integration.py::test_pycas_upload_download -v"

# Clean up
docker compose -f tests/integration-pycas/docker-compose.yml down -v
```

### Local Development (with local pycas)

If you have pycas installed locally:

```bash
# Terminal 1: Start pycas server
uv tool install --from git+https://gitlab.com/ladidadida/pycas pycas
uv tool run pycas serve \
  --host 0.0.0.0 \
  --port 50051 \
  --storage-path /tmp/pycas-test

# Terminal 2: Run tests
CASCADE_CAS_URL=grpc://localhost:50051 uv run pytest tests/integration-pycas/test_pycas_integration.py -v
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
tests/integration-pycas/
├── docker-compose.yml          # Container orchestration
├── test_pycas_integration.py   # Integration test suite
└── README.md                    # This file
```

## CI Integration

See `.github/workflows/pycas-integration.yml` for CI configuration.

## Troubleshooting

### pycas server not starting

Check logs:
```bash
docker compose -f tests/integration-pycas/docker-compose.yml logs pycas
```

### Connection refused

Ensure pycas health check passes:
```bash
docker compose -f tests/integration-pycas/docker-compose.yml ps
```

The `pycas` service should show as "healthy".

### Tests timing out

Increase timeouts in `test_pycas_integration.py` or check pycas logs for errors.

## Development

To add new integration tests:

1. Add test function to `test_pycas_integration.py`
2. Use `pycas_url` fixture for server URL
3. Use `local_cache` fixture for local cache instance
4. Always call `await cas_cache.close()` in finally block
5. Test should be fully self-contained (create/cleanup own artifacts)

## References

- pycas GitLab: https://gitlab.com/ladidadida/pycas
- Remote Execution API: https://github.com/bazelbuild/remote-apis
- Cascade remote cache docs: ../../examples/remote-cache/README.md
