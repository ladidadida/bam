#!/usr/bin/env bash
# Run pycas integration tests with Docker Compose

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

cd "$PROJECT_ROOT"

echo "🚀 Starting pycas integration tests..."
echo "   Using Docker Compose to orchestrate pycas server + cascade client"
echo ""

# Check if Docker Compose is available
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed or not in PATH"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "❌ Error: Docker Compose is not available"
    echo "   Install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# Run tests
echo "📦 Building and starting containers..."
docker compose -f tests/integration-pycas/docker-compose.yml up \
    --abort-on-container-exit \
    --exit-code-from cascade-client

EXIT_CODE=$?

echo ""
echo "🧹 Cleaning up containers..."
docker compose -f tests/integration-pycas/docker-compose.yml down -v

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ All pycas integration tests passed!"
else
    echo ""
    echo "❌ Some tests failed (exit code: $EXIT_CODE)"
fi

exit $EXIT_CODE
