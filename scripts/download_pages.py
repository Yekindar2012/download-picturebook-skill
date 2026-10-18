#!/usr/bin/env python3
"""Download public book images without browser credentials or curl user config."""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

HOSTS = {"online.fliphtml5.com", "online.anyflip.com"}
MAX_PAGE_BYTES = 25 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024


def book_url(value):
    # Reject queries (including signed tokens), userinfo, ports and encoded paths.
    if any(ord(c) < 33 or ord(c) > 126 for c in value):
        raise ValueError("Invalid book URL.")
    u = urlsplit(value)
    if (u.scheme != "https" or u.netloc not in HOSTS or u.query
            or not re.fullmatch(r"/[A-Za-z0-9_-]+/[A-Za-z0-9_-]+/?", u.path)):
        raise ValueError("Use a public HTTPS book URL on an allowed host, without credentials or query parameters.")
    return "https://" + u.netloc + u.path.rstrip("/")


def proxy_url(value):
    # No proxy credential support: a trusted local forwarder can handle upstream auth.
    if not re.fullmatch(r"http://127\.0\.0\.1:[0-9]{1,5}", value):
        raise ValueError("Proxy must be an unauthenticated HTTP loopback address.")
    port = int(value.rsplit(":", 1)[1])
    if not 1 <= port <= 65535:
        raise ValueError("Invalid proxy port.")
    return value


def page_range(start, end):
    if not start.isdecimal() or not end.isdecimal():
        raise ValueError("Page numbers must be integers.")
    first, last = int(start), int(end)
    if not 1 <= first <= last <= 500:
        raise ValueError("Page range must be within 1..500.")
    return range(first, last + 1)


def curl_get(curl, url, target, proxy="", limit=MAX_PAGE_BYTES):
    # -q must be FIRST: ignore ~/.curlrc (cookies, headers, netrc, uploads, tracing).
    # Clean environment: no inherited proxy, TLS key log, preload or credential vars.
    env = {"PATH": "/usr/bin:/bin", "LC_ALL": "C"}
    args = [curl, "-q", "--silent", "--proto", "=https",
            "--proto-redir", "=https", "--max-redirs", "0",
            "--connect-timeout", "10", "--max-time", "60",
            "--max-filesize", str(limit), "--proxy", proxy,
            "--noproxy", "", "--output", str(target),
            "--write-out", "%{http_code}", "--url", url]
    # No -L: reject every redirect, including same-site redirects.
    # Stream with an application-enforced byte limit, independent of curl version.
    args[args.index("--output") + 1] = "-"
    args[args.index("--write-out") + 1] = "\\n%{http_code}"
    proc = subprocess.Popen(args, env=env, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    pending = b""
    written = 0
    try:
        with open(target, "wb") as stream:
            while True:
                chunk = proc.stdout.read(65536)
                if not chunk:
                    break
                pending += chunk
                if len(pending) > 4:
                    data, pending = pending[:-4], pending[-4:]
                    written += len(data)
                    if written > limit:
                        raise RuntimeError("Download size limit exceeded.")
                    stream.write(data)
        if proc.wait(timeout=5) or not re.fullmatch(rb"\n[0-9]{3}", pending):
            raise RuntimeError("Download failed; no response details logged.")
        return pending[1:].decode("ascii")
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.wait()
        proc.stdout.close()


def download(base, pages, output, proxy=""):
    curl = shutil.which("curl")
    if not curl:
        raise RuntimeError("curl is required.")
    # Fresh directory only: never overwrite existing files or follow leaf symlinks.
    output = Path(output)
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    os.chmod(output, 0o700)
    total = 0
    count = 0
    try:
        for n in pages:
            target = output / ("page%d.webp" % n)
            try:
                with target.open("xb"):
                    pass
                os.chmod(target, 0o600)
                remaining = min(MAX_PAGE_BYTES, MAX_TOTAL_BYTES - total)
                if remaining <= 0:
                    raise RuntimeError("Total download limit reached.")
                status = curl_get(curl, base + "/files/large/%d.webp" % n, target, proxy, remaining)
                if status == "404":
                    if not count:
                        raise RuntimeError("No public pages found.")
                    print("End reached (404); verify page completeness against the source.")
                    break
                if status != "200":
                    raise RuntimeError("Download refused: non-200 response or redirect.")
                size = target.stat().st_size
                total += size
                with target.open("rb") as stream:
                    header = stream.read(12)
                if (size > MAX_PAGE_BYTES or total > MAX_TOTAL_BYTES
                        or header[:4] != b"RIFF" or header[8:12] != b"WEBP"):
                    raise RuntimeError("Invalid image or download size limit exceeded.")
                count += 1
                print("page %d ok" % n)
            finally:
                # Remove incomplete/404 responses; outer cleanup handles failures.
                if target.exists() and count < n - pages.start + 1:
                    target.unlink()
        else:
            print("Requested range downloaded; book completeness is NOT confirmed.")
    except BaseException:
        shutil.rmtree(output)
        raise


def main():
    os.umask(0o077)
    if len(sys.argv) not in (5, 6):
        print("Usage: download_pages.py BOOK_URL START END NEW_OUTPUT_DIR [http://127.0.0.1:PORT]", file=sys.stderr)
        return 2
    try:
        base = book_url(sys.argv[1])
        pages = page_range(sys.argv[2], sys.argv[3])
        proxy = proxy_url(sys.argv[5]) if len(sys.argv) == 6 else ""
        download(base, pages, sys.argv[4], proxy)
        return 0
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError):
        # Do not echo URLs, proxy credentials, paths or raw network exceptions.
        print("Download stopped safely. Check public URL, page range, new output directory and network settings.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
