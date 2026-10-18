import importlib.util
import os
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("downloader", ROOT / "scripts/download_pages.py")
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)


class SecurityTests(unittest.TestCase):
    def test_url_policy(self):
        self.assertEqual(d.book_url("https://online.fliphtml5.com/abc/def/#p=1"),
                         "https://online.fliphtml5.com/abc/def")
        for url in ["http://online.fliphtml5.com/a/b", "https://evil.test/a/b",
                    "https://online.fliphtml5.com.evil.test/a/b",
                    "https://user:SECRET@online.fliphtml5.com/a/b",
                    "https://online.fliphtml5.com/a/b?token=SECRET",
                    "https://online.fliphtml5.com:443/a/b",
                    "https://online.fliphtml5.com/a/%2e%2e",
                    "file:///etc/passwd", "https://online.fliphtml5.com/a/b\n"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                d.book_url(url)

    def test_proxy_and_range(self):
        self.assertEqual(d.proxy_url("http://127.0.0.1:7897"), "http://127.0.0.1:7897")
        for value in ["http://user:SECRET@127.0.0.1:7897", "http://evil.test:80",
                      "http://127.0.0.1:0", "http://127.0.0.1:99999"]:
            with self.assertRaises(ValueError):
                d.proxy_url(value)
        for a, b in [("0", "2"), ("1", "501"), ("3", "1"), ("1;echo", "3")]:
            with self.assertRaises(ValueError):
                d.page_range(a, b)

    def test_curl_isolation(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"HTTPS_PROXY": "SECRET", "SSLKEYLOGFILE": "/tmp/secret"}):
            with patch.object(d.subprocess, "Popen") as popen:
                proc = popen.return_value
                proc.stdout = io.BytesIO(b"image\n200")
                proc.wait.return_value = 0
                proc.poll.return_value = 0
                target = Path(tmp) / "out"
                self.assertEqual(d.curl_get("/usr/bin/curl", "https://online.fliphtml5.com/a/b", target), "200")
                self.assertEqual(target.read_bytes(), b"image")
                args = popen.call_args.args[0]
                self.assertEqual(args[1], "-q")
                self.assertNotIn("-L", args)
                self.assertEqual(args[args.index("--proxy") + 1], "")
                self.assertEqual(popen.call_args.kwargs["env"], {"PATH": "/usr/bin:/bin", "LC_ALL": "C"})

    def test_stream_limit(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(d.subprocess, "Popen") as popen:
            proc = popen.return_value
            proc.stdout = io.BytesIO(b"x" * 100 + b"\n200")
            proc.poll.return_value = None
            with self.assertRaises(RuntimeError):
                d.curl_get("/usr/bin/curl", "https://online.fliphtml5.com/a/b", Path(tmp) / "out", limit=10)
            proc.kill.assert_called_once()
            self.assertLessEqual((Path(tmp) / "out").stat().st_size, 10)

    def test_download_permissions_and_404(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "pages"
            def fetch(curl, url, target, proxy, limit):
                target.write_bytes(b"RIFF0000WEBPimage")
                return "200" if url.endswith("2.webp") else "404"
            with patch.object(d, "curl_get", side_effect=fetch):
                d.download("https://online.fliphtml5.com/a/b", range(2, 5), output)
            self.assertEqual([p.name for p in output.iterdir()], ["page2.webp"])
            self.assertEqual(output.stat().st_mode & 0o777, 0o700)
            self.assertEqual((output / "page2.webp").stat().st_mode & 0o777, 0o600)

    def test_redirect_and_bad_image_cleanup(self):
        for status, body in [("302", b"redirect"), ("200", b"<html>private</html>"), ("404", b"missing")]:
            with self.subTest(status=status), tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / "pages"
                def fetch(curl, url, target, proxy, limit):
                    target.write_bytes(body)
                    return status
                with patch.object(d, "curl_get", side_effect=fetch), self.assertRaises(RuntimeError):
                    d.download("https://online.fliphtml5.com/a/b", range(1, 3), output)
                self.assertFalse(output.exists())

    def test_never_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "pages"
            output.mkdir()
            keep = output / "private.txt"
            keep.write_text("keep")
            with self.assertRaises(FileExistsError):
                d.download("https://online.fliphtml5.com/a/b", range(1, 2), output)
            self.assertEqual(keep.read_text(), "keep")

    def test_cli_secret_not_logged(self):
        result = subprocess.run(["python3", "-I", str(ROOT / "scripts/download_pages.py"),
                                 "https://user:SECRET@online.fliphtml5.com/a/b", "1", "2", "unused"],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("SECRET", result.stdout + result.stderr)

    def test_browser_disabled(self):
        result = subprocess.run(["bash", str(ROOT / "scripts/fetch_pages.sh")], capture_output=True)
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
