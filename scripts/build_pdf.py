#!/usr/bin/env python3
# 将绘本页面图（webp，pageN.webp 命名）合成为全画质 PDF
# 用法: build_pdf.py <图片目录> <输出.pdf> [jpeg质量，默认92]
import glob, os, re, sys, shutil, tempfile

src, out_pdf = sys.argv[1], sys.argv[2]
quality = int(sys.argv[3]) if len(sys.argv) > 3 else 92

from PIL import JpegImagePlugin  # 必须先导入以注册 JPEG 保存器（Image.SAVE 默认为空）
from PIL import Image

paths = glob.glob(os.path.join(src, "*.webp"))
paths.sort(key=lambda x: int(re.search(r"page(\d+)\.webp", os.path.basename(x)).group(1)))
assert paths, "no page*.webp found"

tmp = tempfile.mkdtemp(prefix="hbpdf-")
dims = None
for p in paths:
    n = re.search(r"page(\d+)\.webp", os.path.basename(p)).group(1)
    im = Image.open(p).convert("RGB")
    if dims is None:
        dims = im.size
    im.save(os.path.join(tmp, f"p{n}.jpg"), quality=quality)

from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.utils import ImageReader
w, h = dims
c = rl_canvas.Canvas(out_pdf, pagesize=(w, h))
for p in paths:
    n = re.search(r"page(\d+)\.webp", os.path.basename(p)).group(1)
    c.drawImage(ImageReader(os.path.join(tmp, f"p{n}.jpg")), 0, 0, width=w, height=h)
    c.showPage()
c.save()
shutil.rmtree(tmp)
print(f"pdf done: {out_pdf} ({len(paths)} pages, {dims[0]}x{dims[1]})")
