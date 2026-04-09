#!/usr/bin/env bash
# Demo: Task dependency graph
set -e
DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$DEMO_DIR/type"

cd "$DEMO_DIR/../../examples/webproject"

clear
sleep 0.5

_type_and_run "bam --graph"
sleep 1.5
