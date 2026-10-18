#!/bin/bash
# Browser sessions may contain private cookies; this fallback is disabled.
printf '%s\n' 'Browser fallback disabled. Use fetch_pages_direct.sh with a public HTTPS book URL.' >&2
exit 1
