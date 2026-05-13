#!/usr/bin/env bash
# Quick smoke test — delegates to the Python runner for accurate PASS/FAIL classification.
# For full details use: python3 scripts/run_all.py

set -e
cd "$(dirname "$0")/.."
exec python3 scripts/run_all.py
