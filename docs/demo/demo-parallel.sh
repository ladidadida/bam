#!/usr/bin/env bash
# Demo: Parallel execution with live progress tree
set -e
DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$DEMO_DIR/type"

cd "$DEMO_DIR/../../examples/webproject"
rm -rf .bam

clear
sleep 0.5

_type_and_run "bam build -j auto"
sleep 1.5
