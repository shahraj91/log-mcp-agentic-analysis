#!/usr/bin/env bash
set -e
source .venv/bin/activate
python3 server.py &
SERVER_PID=$!
sleep 1
python3 local_triage.py --log large_sample.log || true
kill $SERVER_PID
