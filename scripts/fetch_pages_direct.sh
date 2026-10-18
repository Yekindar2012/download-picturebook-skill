#!/bin/bash
# Compatibility entry point; never enable shell tracing with private arguments.
set -eu
exec python3 -I "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/download_pages.py" "$@"
