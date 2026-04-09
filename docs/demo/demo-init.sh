#!/usr/bin/env bash
# Demo: bam --init wizard
set -e
DEMO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$DEMO_DIR/type"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

# Copy stub files so detection works
cp "$DEMO_DIR/../../examples/webproject/package.json" "$TMPDIR/"

cd "$TMPDIR"

clear
sleep 0.5

_type_and_run "bam --init <<< '3'"
sleep 0.8

_type_and_run "cat bam.yaml"
sleep 1.5
