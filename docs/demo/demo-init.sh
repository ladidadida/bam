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

# Show the command being typed, then hand off to pexpect for the interactive prompt
printf '\e[1;32m$\e[0m '
cmd="bam --init"
for (( i=0; i<${#cmd}; i++ )); do
    printf '%s' "${cmd:$i:1}"
    sleep 0.04
done
echo
sleep 0.3

python3 - <<'EOF'
import pexpect, sys, time

child = pexpect.spawn("bam --init", encoding="utf-8", timeout=10)
child.logfile_read = sys.stdout  # only echo child output, not our input

child.expect(r"Select a template \[")
time.sleep(1.8)
child.sendline("3")  # terminal PTY echoes this naturally

child.expect(pexpect.EOF)
EOF

sleep 1.5
