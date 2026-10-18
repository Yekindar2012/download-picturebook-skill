#!/usr/bin/env python3
"""Convert task-owned WebP pages to a private PDF, without network access."""
import io
import os
import re
import sys
import warnings
from pathlib import Path


def build(src, output, quality=92):
    from PIL import Image
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader

    Image.MAX_IMAGE_PIXELS = 40_000_000
    warnings.simplefilter("error", Image.DecompressionBombWarning)
    src, output = Path(src), Path(output)
    if src.is_symlink() or not src.is_dir():
        raise ValueError("Invalid input directory.")
    paths = sorted((p for p in src.iterdir() if re.fullmatch(r"page[0-9]+\.webp", p.name)),
                   key=lambda p: int(p.stem[4:]))
    if not paths or len(paths) > 500 or not 1 <= quality <= 100:
        raise ValueError("Invalid pages or quality.")
    if any(p.is_symlink() or not p.is_file() or p.stat().st_size > 25 * 1024 * 1024 for p in paths):
        raise ValueError("Invalid input image.")
    created = False
    try:
        # Exclusive create rejects existing paths and symlinks; private mode from open.
        fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        created = True
        with os.fdopen(fd, "wb") as stream:
            pdf = canvas.Canvas(stream)
            pdf.setTitle("Picture book")
            pdf.setAuthor("")
            for path in paths:
                with Image.open(path) as original:
                    if original.format != "WEBP":
                        raise ValueError("Expected WebP.")
                    with original.convert("RGBA") as rgba:
                        im = Image.new("RGB", rgba.size, "white")
                        im.paste(rgba, mask=rgba.getchannel("A"))
                with im:
                    with io.BytesIO() as encoded:
                        im.save(encoded, format="JPEG", quality=quality)
                        encoded.seek(0)
                        w, h = im.size
                        pdf.setPageSize((w, h))
                        pdf.drawImage(ImageReader(encoded), 0, 0, width=w, height=h)
                        pdf.showPage()
            pdf.save()
    except BaseException:
        if created:
            output.unlink(missing_ok=True)
        raise
    print("PDF created (%d pages)." % len(paths))


if __name__ == "__main__":
    os.umask(0o077)
    try:
        if len(sys.argv) not in (3, 4):
            raise ValueError("Invalid arguments.")
        build(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) == 4 else 92)
    except Exception:
        print("PDF creation failed. Check inputs and Pillow/reportlab installation.", file=sys.stderr)
        sys.exit(1)
