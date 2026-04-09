#!/usr/bin/env bash
# Demo: Interactive foreground task (dev server)
set -e
DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$DEMO_DIR/type"

cd "$DEMO_DIR/../../examples/webproject"
rm -rf .bam

# Populate cache silently so the serve scene shows cached deps
bam build -j auto -q

clear
sleep 0.5

_type_and_run "bam serve"
sleep 1.5
